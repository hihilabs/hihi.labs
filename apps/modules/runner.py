"""Module runner — clone, build, and run a module's repo as a local
docker container, traefik-labeled at <slug>.local.hihilabs.xyz.

Lifecycle runs in a background thread (builds take minutes); progress and
errors stream into ModuleInstance.log so the card UI can poll. Clones live
under module_runs/<slug> (mounted at /workspace inside the app container,
SANDBOX-style host-path translation for the docker daemon's bind mounts).
"""
import os
import re
import socket
import subprocess
import threading

from django.conf import settings

RUNS_BASE = os.environ.get('MODULE_RUNS_BASE', '/workspace/module_runs')
RUNS_HOST_BASE = os.environ.get('MODULE_RUNS_HOST_BASE',
                                '/mnt/user/appdata/hihilabs/module_runs')
BIND_IP = os.environ.get('SANDBOX_BIND_IP', '192.168.0.28')
LOCAL_DOMAIN = os.environ.get('MODULE_LOCAL_DOMAIN', 'local.hihilabs.xyz')
PORT_RANGE = range(8201, 8261)

GENERATED_DJANGO_DOCKERFILE = """\
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD python manage.py migrate --noinput; python manage.py runserver 0.0.0.0:8000
"""

GENERATED_NODE_DOCKERFILE = """\
FROM node:20-slim
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
"""

GENERATED_STATIC_DOCKERFILE = """\
FROM python:3.12-slim
WORKDIR /site
COPY . .
EXPOSE 8000
CMD ["python", "-m", "http.server", "8000", "--directory", "/site"]
"""


def _docker():
    import docker
    return docker.from_env()


def _log(inst, line):
    inst.log = (inst.log + line.rstrip() + '\n')[-20000:]
    inst.save(update_fields=['log', 'status', 'updated_at'])


def _set_status(inst, status, line=None):
    inst.status = status
    if line:
        _log(inst, line)
    else:
        inst.save(update_fields=['status', 'updated_at'])


def _clone_url(module):
    """https clone URL; token-authed for private repos (never logged)."""
    url = module.github_url or module.source_url
    if not url:
        raise ValueError('module has no repo URL')
    if module.is_private and settings.GITHUB_TOKEN:
        return url.replace('https://', f'https://x-access-token:{settings.GITHUB_TOKEN}@') + '.git'
    return url + ('.git' if not url.endswith('.git') else '')


def _free_port(used):
    for p in PORT_RANGE:
        if p in used:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((BIND_IP, p)) != 0:
                return p
    raise RuntimeError('no free module ports (8201-8260)')


def _internal_port(workdir):
    """EXPOSE from the Dockerfile, else 8000."""
    try:
        text = open(os.path.join(workdir, 'Dockerfile')).read()
        m = re.search(r'^EXPOSE\s+(\d+)', text, re.M)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return 8000


def _ensure_recipe(inst, workdir):
    """Use the repo's Dockerfile, or generate one for known stacks."""
    if os.path.exists(os.path.join(workdir, 'Dockerfile')):
        _log(inst, '• using repo Dockerfile')
        return
    if os.path.exists(os.path.join(workdir, 'manage.py')):
        if not os.path.exists(os.path.join(workdir, 'requirements.txt')):
            open(os.path.join(workdir, 'requirements.txt'), 'w').write(
                'django\npillow\npython-decouple\npython-dotenv\nrequests\n'
                'whitenoise\ndj-database-url\n')
            _log(inst, '• no requirements.txt — generated best-guess one '
                       '(django/pillow/decouple/dotenv/requests/whitenoise)')
        open(os.path.join(workdir, 'Dockerfile'), 'w').write(GENERATED_DJANGO_DOCKERFILE)
        _log(inst, '• no Dockerfile — generated Django recipe (runserver :8000)')
        return
    if os.path.exists(os.path.join(workdir, 'package.json')):
        open(os.path.join(workdir, 'Dockerfile'), 'w').write(GENERATED_NODE_DOCKERFILE)
        _log(inst, '• no Dockerfile — generated Node recipe (npm start :3000)')
        return
    if os.path.exists(os.path.join(workdir, 'index.html')):
        open(os.path.join(workdir, 'Dockerfile'), 'w').write(GENERATED_STATIC_DOCKERFILE)
        _log(inst, '• no Dockerfile — generated static recipe (http.server :8000)')
        return
    raise RuntimeError('no Dockerfile and no recognizable stack '
                       '(need Dockerfile, manage.py+requirements.txt, '
                       'package.json, or index.html)')


def _lifecycle(inst):
    from .models import ModuleInstance
    module = inst.module
    slug = module.slug
    workdir = os.path.join(RUNS_BASE, slug)
    try:
        # ── clone / update ───────────────────────────────────────────────
        _set_status(inst, 'cloning', f'» cloning {module.github_name or slug} '
                                     f'({module.default_branch})')
        url = _clone_url(module)
        if os.path.isdir(os.path.join(workdir, '.git')):
            cmds = [['git', '-C', workdir, 'fetch', 'origin'],
                    ['git', '-C', workdir, 'reset', '--hard',
                     f'origin/{module.default_branch}']]
        else:
            os.makedirs(RUNS_BASE, exist_ok=True)
            cmds = [['git', 'clone', '--depth', '1', '-b', module.default_branch,
                     url, workdir]]
        for cmd in cmds:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise RuntimeError('git failed: ' +
                                   (r.stderr or r.stdout).replace(settings.GITHUB_TOKEN or '∅', '***')[-500:])
        _log(inst, '• clone/update ok')

        # ── build ────────────────────────────────────────────────────────
        _set_status(inst, 'building', '» building image')
        _ensure_recipe(inst, workdir)
        client = _docker()
        try:
            _, build_log = client.images.build(path=workdir, tag=f'module-{slug}',
                                               rm=True, forcerm=True)
            for chunk in build_log:
                line = (chunk.get('stream') or '').strip()
                if line.startswith('Step'):
                    _log(inst, '  ' + line)
        except Exception as e:
            raise RuntimeError(f'build failed: {str(e)[-600:]}')
        _log(inst, '• image built')

        # ── run ──────────────────────────────────────────────────────────
        used = set(ModuleInstance.objects.filter(status='running')
                   .exclude(pk=inst.pk).values_list('port', flat=True))
        port = _free_port(used)
        internal = _internal_port(workdir)
        name = f'module-{slug}'
        host = f'{slug}.{LOCAL_DOMAIN}'
        try:
            old = client.containers.get(name)
            old.remove(force=True)
        except Exception:
            pass
        client.containers.run(
            f'module-{slug}', name=name, detach=True,
            ports={f'{internal}/tcp': (BIND_IP, port)},
            mem_limit='1g', nano_cpus=2_000_000_000,
            restart_policy={'Name': 'unless-stopped'},
            network='traefik',
            labels={
                'traefik.enable': 'true',
                f'traefik.http.routers.module-{slug}.rule': f'Host(`{host}`)',
                f'traefik.http.routers.module-{slug}.entrypoints': 'websecure',
                f'traefik.http.routers.module-{slug}.tls': 'true',
                f'traefik.http.services.module-{slug}.loadbalancer.server.port': str(internal),
            },
            environment={
                'PORT': str(internal),
                'ALLOWED_HOSTS': f'{host},localhost,*',
                # dev-instance defaults so decouple/os.environ-style settings boot
                'SECRET_KEY': f'local-dev-{slug}-not-secret',
                'DEBUG': 'True',
                'CSRF_TRUSTED_ORIGINS': f'https://{host},http://localhost',
            },
        )
        inst.container = name
        inst.port = port
        inst.host = host
        inst.save(update_fields=['container', 'port', 'host', 'updated_at'])

        # health check: container alive AND something listening on the port
        # (a wedged runserver reloader keeps the container "running" while dead)
        import time
        listening = False
        for _ in range(6):
            time.sleep(5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                if s.connect_ex((BIND_IP, port)) == 0:
                    listening = True
                    break
        c = client.containers.get(name)
        c.reload()
        if not listening or c.status != 'running':
            tail = c.logs(tail=20).decode(errors='replace')
            c.remove(force=True)
            raise RuntimeError('app failed to come up on its port:\n' + tail[-900:])
        _set_status(inst, 'running',
                    f'✓ running — https://{host}/ (traefik) · http://{BIND_IP}:{port}/ (direct)')
    except Exception as e:
        _set_status(inst, 'error', f'✗ {e}')


def start(module, user):
    """Create/refresh the instance row and kick off the lifecycle thread."""
    from .models import ModuleInstance
    inst, _ = ModuleInstance.objects.update_or_create(
        module=module,
        defaults={'status': 'cloning', 'log': '', 'started_by': user},
    )
    threading.Thread(target=_lifecycle, args=(inst,), daemon=True).start()
    return inst


def stop(inst):
    try:
        c = _docker().containers.get(inst.container)
        c.remove(force=True)
    except Exception:
        pass
    inst.status = 'stopped'
    inst.save(update_fields=['status', 'updated_at'])

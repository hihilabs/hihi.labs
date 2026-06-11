"""Sandbox engine — spin throwaway dev containers from a room.

Runs against the host docker daemon (docker.sock is mounted into the app
container). Each sandbox gets a workspace dir under SANDBOX_BASE that is
bind-mounted into its container; the room's file API edits those files and
the dev server inside picks changes up (runserver autoreload / fresh static
serve). Ports bind to the LAN IP only.
"""
import os
import socket
from pathlib import Path

# Inside the app container the project root is mounted at /workspace; the same
# dir on the HOST is the compose project dir — docker needs host paths for binds.
SANDBOX_BASE = Path(os.environ.get('SANDBOX_BASE', '/workspace/sandboxes'))
SANDBOX_HOST_BASE = os.environ.get('SANDBOX_HOST_BASE', '/mnt/user/appdata/hihilabs/sandboxes')
SANDBOX_BIND_IP = os.environ.get('SANDBOX_BIND_IP', '192.168.0.28')
PORT_RANGE = range(8101, 8131)

_DJANGO_SETTINGS = """\
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'sandbox-not-secret'
DEBUG = True
ALLOWED_HOSTS = ['*']
INSTALLED_APPS = ['django.contrib.staticfiles']
ROOT_URLCONF = 'proj.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates',
              'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': False,
              'OPTIONS': {'context_processors': []}}]
STATIC_URL = '/static/'
DATABASES = {}
USE_TZ = True
"""

_DJANGO_URLS = """\
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path
import datetime

def home(request):
    return render(request, 'index.html')

def api_time(request):
    return JsonResponse({'now': datetime.datetime.now().strftime('%H:%M:%S')})

urlpatterns = [
    path('', home),
    path('api/time/', api_time),
]
"""

_DJANGO_INDEX = """\
<!doctype html>
<html>
<head>
  <title>django + htmx sandbox</title>
  <script src="https://unpkg.com/htmx.org@2"></script>
  <style>body{font-family:monospace;background:#0a0a0c;color:#e8e8ea;display:grid;place-items:center;height:100vh;margin:0}
  button{background:#7c6af7;color:#fff;border:0;padding:10px 18px;border-radius:6px;cursor:pointer;font-family:inherit}
  #out{margin-top:16px;color:#34d399}</style>
</head>
<body>
  <main style="text-align:center">
    <h1>django + htmx</h1>
    <p>Edit me from the room. runserver autoreloads.</p>
    <button hx-get="/api/time/" hx-target="#out">what time is it?</button>
    <div id="out"></div>
  </main>
</body>
</html>
"""

_STATIC_INDEX = """\
<!doctype html>
<html>
<head><title>static sandbox</title>
<style>body{font-family:monospace;background:#0a0a0c;color:#e8e8ea;display:grid;place-items:center;height:100vh;margin:0}</style>
</head>
<body><h1>static sandbox — edit me from the room</h1></body>
</html>
"""

TEMPLATES = {
    'django-htmx': {
        'label': 'Django + HTMX',
        'desc': 'Django dev server with an htmx starter page (house default)',
        'image': 'hihilabs',  # reuses the app image — django preinstalled
        'cmd': ['python', 'manage.py', 'runserver', '0.0.0.0:8000'],
        'mount_to': '/site',
        'workdir': '/site',
        'seed': {
            'manage.py': ("#!/usr/bin/env python\nimport os, sys\n"
                          "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proj.settings')\n"
                          "from django.core.management import execute_from_command_line\n"
                          "execute_from_command_line(sys.argv)\n"),
            'proj/__init__.py': '',
            'proj/settings.py': _DJANGO_SETTINGS,
            'proj/urls.py': _DJANGO_URLS,
            'templates/index.html': _DJANGO_INDEX,
        },
    },
    'static': {
        'label': 'Static site',
        'desc': 'Plain HTML/CSS/JS served by python http.server',
        'image': 'python:3.12-slim',
        'cmd': ['python', '-m', 'http.server', '8000', '--directory', '/site'],
        'mount_to': '/site',
        'workdir': '/site',
        'seed': {'index.html': _STATIC_INDEX},
    },
}


def _docker():
    import docker
    return docker.from_env()


def _free_port(used):
    for p in PORT_RANGE:
        if p in used:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((SANDBOX_BIND_IP, p)) != 0:
                return p
    raise RuntimeError('No free sandbox ports')


def spin(board, template_key, user):
    from .models import Sandbox
    tpl = TEMPLATES.get(template_key)
    if not tpl:
        raise ValueError(f'Unknown template "{template_key}" — options: {", ".join(TEMPLATES)}')

    sb = Sandbox.objects.create(board=board, template=template_key,
                                created_by=user, status='running')
    workdir = SANDBOX_BASE / str(sb.pk)
    for rel, content in tpl['seed'].items():
        path = workdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    used = set(Sandbox.objects.filter(status='running').exclude(pk=sb.pk)
               .values_list('port', flat=True))
    port = _free_port(used)
    name = f'sandbox-{sb.pk}'
    try:
        _docker().containers.run(
            tpl['image'], tpl['cmd'], name=name, detach=True,
            working_dir=tpl['workdir'],
            volumes={f'{SANDBOX_HOST_BASE}/{sb.pk}': {'bind': tpl['mount_to'], 'mode': 'rw'}},
            ports={'8000/tcp': (SANDBOX_BIND_IP, port)},
            mem_limit='512m', nano_cpus=1_000_000_000,
            restart_policy={'Name': 'no'},
            environment={'PYTHONUNBUFFERED': '1'},
        )
    except Exception:
        sb.status = 'error'
        sb.save(update_fields=['status'])
        raise
    sb.container = name
    sb.port = port
    sb.save(update_fields=['container', 'port'])
    return sb


def stop(sb):
    try:
        c = _docker().containers.get(sb.container)
        c.remove(force=True)
    except Exception:
        pass
    sb.status = 'stopped'
    sb.save(update_fields=['status'])


def url_for(sb):
    return f'http://{SANDBOX_BIND_IP}:{sb.port}/'


def safe_path(sb, rel):
    """Resolve a workspace-relative path, refusing traversal outside it."""
    root = (SANDBOX_BASE / str(sb.pk)).resolve()
    p = (root / rel.lstrip('/')).resolve()
    if root != p and root not in p.parents:
        raise ValueError('Path outside sandbox')
    return p


def list_files(sb):
    root = SANDBOX_BASE / str(sb.pk)
    out = []
    for p in sorted(root.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            out.append(str(p.relative_to(root)))
    return out

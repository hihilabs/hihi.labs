import subprocess
import os
from django.conf import settings

SSH_OPTS = [
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'ConnectTimeout=8',
    '-o', 'BatchMode=yes',
]


def _ssh_key():
    return getattr(settings, 'GITNODE_SSH_KEY', '/app/ssh/id_ed25519_unraid')


SSH_BIN = '/usr/bin/ssh'


def _ssh_base(server):
    cmd = [SSH_BIN, '-i', _ssh_key()] + SSH_OPTS
    if server.port != 22:
        cmd += ['-p', str(server.port)]
    cmd.append(f'{server.ssh_user}@{server.host}')
    return cmd


def run(server, remote_cmd, timeout=30):
    """Run a command on a remote server. Returns (success, output)."""
    cmd = _ssh_base(server) + [remote_cmd]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, f'Timed out after {timeout}s'
    except FileNotFoundError:
        return False, 'ssh not found — is openssh-client installed in the container?'
    except Exception as e:
        return False, str(e)


def git_status(server, path):
    ok, out = run(server, f'git -C {path} status --short')
    return out if ok else f'error: {out}'


def git_log(server, path, n=5):
    ok, out = run(server, f'git -C {path} log --oneline -{n} --decorate')
    return out if ok else f'error: {out}'


def git_branch(server, path):
    ok, out = run(server, f'git -C {path} branch --show-current')
    return out.strip() if ok else '?'


def scoop(server, path, message):
    """Stage all, commit, push. Returns (success, output)."""
    safe_msg = message.replace("'", "\\'")
    cmd = (
        f'cd {path} && '
        f'if [ -n "$(git status --porcelain)" ]; then '
        f'  git add -A && '
        f'  git commit -m \'{safe_msg}\' && '
        f'  git push && '
        f'  echo "SCOOPED"; '
        f'else '
        f'  echo "CLEAN"; '
        f'fi'
    )
    return run(server, cmd, timeout=60)


def deploy(server, path, service_name):
    """Pull latest, restart service. Returns (success, output)."""
    cmd = f'git -C {path} pull'
    if service_name:
        cmd += f' && systemctl restart {service_name}'
    return run(server, cmd, timeout=60)

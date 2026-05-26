import json
import subprocess
from datetime import date
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.projects.models import Project, Task, TimeEntry
from apps.servers.models import Server

WORKSPACE = Path('/workspace')
APP_DIR = Path('/app')

DEFINITIONS = [
    {
        "name": "list_projects",
        "description": "List all projects with status, hours logged, unbilled hours, and task counts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "done", "archived"],
                    "description": "Filter by status. Omit for all.",
                },
            },
        },
    },
    {
        "name": "get_project",
        "description": "Get full detail for one project: all tasks, recent time entries, hour totals.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "Project primary key"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "create_project",
        "description": "Create a new project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "client": {"type": "string"},
                "description": {"type": "string"},
                "hourly_rate": {"type": "number", "description": "Default 150"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "create_task",
        "description": "Create a task on a project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "title": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                "notes": {"type": "string"},
                "due_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["project_id", "title"],
        },
    },
    {
        "name": "update_task",
        "description": "Update a task status, priority, or notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["todo", "doing", "blocked", "done"]},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                "notes": {"type": "string"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "list_servers",
        "description": "List all registered servers with SSH connection info.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_active_timer",
        "description": "Get the currently running time entry, if any.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "start_timer",
        "description": "Start a time entry on a project. Stops any currently running timer first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "task_id": {"type": "integer", "description": "Optional task to link to"},
                "description": {"type": "string"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "stop_timer",
        "description": "Stop the currently running time entry.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_file",
        "description": (
            "Read a source file from the hihilabs project. "
            "Use relative paths like 'apps/claude_ai/views.py' or 'templates/base.html'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path within the project"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a source file in the hihilabs project. "
            "Always read the file first. Write the complete file content — not a diff. "
            "After writing, tell Andrew to rebuild: docker compose up -d --build"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path within the project"},
                "content": {"type": "string", "description": "Complete file content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_dir",
        "description": "List files and directories at a path in the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path. Default '.'"},
            },
        },
    },
    {
        "name": "run_manage",
        "description": "Run a Django management command (migrate, makemigrations, showmigrations, check).",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command and args, e.g. 'makemigrations claude_ai'"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "docker_rebuild",
        "description": (
            "Rebuild and restart the hihilabs container. Use this after writing static files (CSS/JS) "
            "or requirements.txt changes. Python and template changes hot-reload automatically — "
            "no rebuild needed for those. Takes ~60-90 seconds."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_files",
        "description": (
            "Search for a string or pattern across the project source files (Python, HTML, JS, CSS, etc). "
            "Returns matching lines with file paths and line numbers. Use this to find where something is "
            "defined or used before editing it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text or regex to search for"},
                "path": {"type": "string", "description": "Subdirectory to search in (default '.')"},
                "case_sensitive": {"type": "boolean", "description": "Default true"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "git_status",
        "description": "Show current git status — which files are modified, staged, or untracked.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "git_diff",
        "description": "Show a git diff of all unstaged changes, so you can see exactly what was modified.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "git_commit",
        "description": (
            "Stage all modified/new files and create a git commit. "
            "Use after a set of related edits is complete and tested."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Commit message describing the change"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "trigger_deploy",
        "description": (
            "Trigger a live deploy on the production server: git pull + gunicorn reload. "
            "Use after git_commit to push changes live. "
            "Pass cmd='rebuild' to do a full docker rebuild instead (needed for static/requirements changes). "
            "Pass cmd='full' for git pull + docker rebuild."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "enum": ["deploy", "rebuild", "full"],
                    "description": "deploy=git pull+reload (default), rebuild=docker build, full=pull+rebuild",
                },
            },
        },
    },
    {
        "name": "loyd",
        "description": (
            "Submit a task to Loyd — the internal GPU AI. "
            "Loyd auto-routes: small tasks → Claude cloud, large context (log files, big dumps) → local GPU Ollama. "
            "Use for: security scans, error log triage, code review, summarization, anything needing AI but too large or too cheap for direct Claude. "
            "Returns the result when complete (polls up to 90s)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt":     {"type": "string", "description": "The instruction or question."},
                "context":    {"type": "string", "description": "Supporting text, log content, code, etc. Can be very large."},
                "system":     {"type": "string", "description": "Optional system prompt override."},
                "tags":       {"type": "array", "items": {"type": "string"}, "description": "e.g. ['security','error_log','code_review']"},
                "model":      {"type": "string", "enum": ["auto", "cloud", "local"], "description": "Force backend. Default: auto."},
                "max_tokens": {"type": "integer", "description": "Max response tokens. Default 2048."},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "write_memory",
        "description": (
            "Store a persistent fact that will be injected into every future conversation. "
            "Use for ongoing context: active projects, current priorities, user preferences, "
            "pending decisions, system state. Key should be short and descriptive (e.g. 'active_project', 'plex_status')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short identifier, snake_case"},
                "value": {"type": "string", "description": "Value to store. Overrides any previous value for this key."},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "delete_memory",
        "description": "Delete a persistent memory note by key.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
            },
            "required": ["key"],
        },
    },
    {
        "name": "ssh_run",
        "description": (
            "SSH into a registered server and run a shell command. "
            "Use list_servers to find server names. "
            "Good for checking logs, running commands on VPS, managing remote services."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string", "description": "Server name or hostname (partial match ok)"},
                "command": {"type": "string", "description": "Shell command to run"},
            },
            "required": ["server", "command"],
        },
    },
]


def execute(user, name, args):
    fn = _HANDLERS.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    try:
        return fn(user, **args)
    except Exception as e:
        return {"error": str(e)}


# ── Data tools ────────────────────────────────────────────────────────────────

def _list_projects(user, status=None):
    qs = Project.objects.filter(owner=user)
    if status:
        qs = qs.filter(status=status)
    return {
        "projects": [
            {
                "id": p.pk,
                "name": p.name,
                "client": p.client,
                "status": p.status,
                "hourly_rate": float(p.hourly_rate),
                "total_hours": p.total_hours(),
                "unbilled_hours": p.unbilled_hours(),
                "tasks_total": p.tasks.count(),
                "tasks_todo": p.tasks.filter(status="todo").count(),
                "tasks_doing": p.tasks.filter(status="doing").count(),
                "tasks_blocked": p.tasks.filter(status="blocked").count(),
            }
            for p in qs
        ],
    }


def _get_project(user, project_id):
    try:
        p = Project.objects.get(pk=project_id, owner=user)
    except Project.DoesNotExist:
        return {"error": "Project not found"}

    tasks = [
        {
            "id": t.pk,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "notes": t.notes,
            "due_date": str(t.due_date) if t.due_date else None,
            "hours": t.total_hours(),
        }
        for t in p.tasks.all()
    ]

    recent = [
        {
            "id": e.pk,
            "description": e.description,
            "started": e.started_at.strftime("%Y-%m-%d %H:%M"),
            "duration": e.duration_display(),
            "billed": e.billed,
        }
        for e in p.time_entries.filter(ended_at__isnull=False)[:10]
    ]

    return {
        "id": p.pk,
        "name": p.name,
        "client": p.client,
        "status": p.status,
        "description": p.description,
        "hourly_rate": float(p.hourly_rate),
        "total_hours": p.total_hours(),
        "unbilled_hours": p.unbilled_hours(),
        "tasks": tasks,
        "recent_time_entries": recent,
    }


def _create_project(user, name, client="", description="", hourly_rate=150):
    p = Project.objects.create(
        owner=user,
        name=name,
        client=client,
        description=description,
        hourly_rate=hourly_rate,
    )
    return {"id": p.pk, "name": p.name, "created": True}


def _create_task(user, project_id, title, priority="normal", notes="", due_date=None):
    try:
        p = Project.objects.get(pk=project_id, owner=user)
    except Project.DoesNotExist:
        return {"error": "Project not found"}

    due = None
    if due_date:
        try:
            due = date.fromisoformat(due_date)
        except ValueError:
            pass

    t = Task.objects.create(project=p, title=title, priority=priority, notes=notes, due_date=due)
    return {"id": t.pk, "title": t.title, "project": p.name, "created": True}


def _update_task(user, task_id, status=None, priority=None, notes=None):
    try:
        t = Task.objects.get(pk=task_id, project__owner=user)
    except Task.DoesNotExist:
        return {"error": "Task not found"}

    if status:
        t.status = status
        if status == "done":
            t.completed_at = timezone.now()
    if priority:
        t.priority = priority
    if notes is not None:
        t.notes = notes
    t.save()
    return {"id": t.pk, "title": t.title, "status": t.status, "updated": True}


def _list_servers(user):
    return {
        "servers": [
            {
                "id": s.pk,
                "name": s.name,
                "host": s.host,
                "ssh_user": s.ssh_user,
                "port": s.port,
                "tags": s.tag_list(),
                "notes": s.notes,
                "ssh_command": s.ssh_command(),
            }
            for s in Server.objects.filter(owner=user)
        ],
    }


def _get_active_timer(user):
    try:
        e = TimeEntry.objects.filter(owner=user, ended_at__isnull=True).latest("started_at")
        elapsed = int((timezone.now() - e.started_at).total_seconds())
        h, rem = divmod(elapsed, 3600)
        m = rem // 60
        return {
            "running": True,
            "id": e.pk,
            "project": e.project.name,
            "project_id": e.project_id,
            "task": e.task.title if e.task else None,
            "description": e.description,
            "started": e.started_at.strftime("%Y-%m-%d %H:%M"),
            "elapsed": f"{h}h {m:02d}m" if h else f"{m}m",
        }
    except TimeEntry.DoesNotExist:
        return {"running": False}


def _start_timer(user, project_id, task_id=None, description=""):
    TimeEntry.objects.filter(owner=user, ended_at__isnull=True).update(ended_at=timezone.now())
    try:
        p = Project.objects.get(pk=project_id, owner=user)
    except Project.DoesNotExist:
        return {"error": "Project not found"}

    task = None
    if task_id:
        try:
            task = Task.objects.get(pk=task_id, project=p)
        except Task.DoesNotExist:
            pass

    e = TimeEntry.objects.create(owner=user, project=p, task=task, description=description)
    return {"started": True, "id": e.pk, "project": p.name}


def _stop_timer(user):
    n = TimeEntry.objects.filter(owner=user, ended_at__isnull=True).update(ended_at=timezone.now())
    return {"stopped": n > 0, "entries_stopped": n}


# ── File / dev tools ──────────────────────────────────────────────────────────

def _resolve_read(rel):
    p = Path(rel.lstrip("/"))
    for base in (WORKSPACE, APP_DIR):
        candidate = (base / p).resolve()
        if candidate.exists():
            return candidate
    return None


def _read_file(user, path):
    resolved = _resolve_read(path)
    if resolved is None:
        return {"error": f"File not found: {path}"}
    try:
        content = resolved.read_text(errors="replace")
        return {"path": path, "lines": content.count("\n") + 1, "content": content}
    except Exception as e:
        return {"error": str(e)}


def _write_file(user, path, content):
    p = Path(path.lstrip("/"))
    target = (WORKSPACE / p).resolve()
    # Safety: must stay inside workspace
    if not str(target).startswith(str(WORKSPACE.resolve())):
        return {"error": "Path escapes workspace"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return {"written": True, "path": str(p), "bytes": len(content)}


def _list_dir(user, path="."):
    p = Path(path.lstrip("/"))
    for base in (WORKSPACE, APP_DIR):
        candidate = (base / p).resolve()
        if candidate.is_dir():
            items = []
            for item in sorted(candidate.iterdir()):
                if item.name.startswith(".") or item.name == "__pycache__":
                    continue
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            return {"path": path, "items": items}
    return {"error": f"Directory not found: {path}"}


_ALLOWED_MANAGE = {
    "migrate", "makemigrations", "showmigrations", "check", "diffsettings",
    "collectstatic", "test", "inspectdb", "sqlmigrate",
}


def _run_manage(user, command):
    parts = command.split()
    if not parts or parts[0] not in _ALLOWED_MANAGE:
        return {"error": f"'{parts[0] if parts else ''}' not in allowlist: {sorted(_ALLOWED_MANAGE)}"}
    result = subprocess.run(
        ["python", "/app/manage.py"] + parts,
        capture_output=True, text=True, timeout=60,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-1000:],
    }


def _trigger_deploy(user, cmd="deploy"):
    import requests as _requests
    url = settings.DEPLOY_WEBHOOK_URL
    secret = settings.DEPLOY_WEBHOOK_SECRET
    if not secret:
        return {"error": "DEPLOY_WEBHOOK_SECRET not configured"}
    try:
        resp = _requests.post(
            url,
            data={"cmd": cmd},
            headers={"Authorization": f"Bearer {secret}"},
            timeout=120,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def _write_memory(user, key, value):
    from .models import MemoryNote
    note, created = MemoryNote.objects.update_or_create(
        user=user, key=key, defaults={'value': value}
    )
    return {"key": key, "saved": True, "created": created}


def _delete_memory(user, key):
    from .models import MemoryNote
    n, _ = MemoryNote.objects.filter(user=user, key=key).delete()
    return {"key": key, "deleted": n > 0}


def args_preview(name, args):
    """Short human-readable description of tool call args for UI display."""
    if name in ('read_file', 'write_file', 'list_dir'):
        return args.get('path', '')[:60]
    if name == 'search_files':
        return f'"{args.get("query", "")}"'
    if name == 'ssh_run':
        return f'{args.get("server", "")} → {args.get("command", "")[:35]}'
    if name == 'run_manage':
        return args.get('command', '')
    if name == 'git_commit':
        return args.get('message', '')[:50]
    if name == 'write_memory':
        return args.get('key', '')
    if name == 'delete_memory':
        return args.get('key', '')
    if name == 'trigger_deploy':
        return args.get('cmd', 'deploy')
    if name == 'loyd':
        return args.get('prompt', '')[:60]
    if name == 'get_project':
        return f'project #{args.get("project_id", "")}'
    if name == 'create_task':
        return args.get('title', '')[:40]
    if name == 'update_task':
        return f'task #{args.get("task_id", "")} → {args.get("status", "")}'
    return ''


def result_preview(name, result):
    """Short human-readable summary of tool result for UI display."""
    if isinstance(result, dict) and 'error' in result:
        return f'error: {result["error"][:60]}'
    if name == 'read_file':
        return f'{result.get("lines", "?")} lines'
    if name == 'write_file':
        return f'{result.get("bytes", 0)} bytes written'
    if name == 'search_files':
        m = result.get('matches', 0)
        return f'{m} match{"es" if m != 1 else ""}'
    if name == 'git_commit':
        return 'committed' if result.get('success') else f'failed: {result.get("output","")[:40]}'
    if name == 'git_status':
        s = result.get('status', '').strip()
        return s[:80] if s and s != '(clean)' else 'clean'
    if name == 'trigger_deploy':
        return result.get('status', str(result)[:40])
    if name == 'run_manage':
        rc = result.get('returncode', -1)
        return 'ok' if rc == 0 else f'exit {rc}'
    if name == 'docker_rebuild':
        return 'rebuilt' if result.get('success') else 'failed'
    if name == 'ssh_run':
        out = result.get('stdout', '').strip()[:60]
        return out or f'exit {result.get("exit_code", 0)}'
    if name == 'list_projects':
        return f'{len(result.get("projects", []))} projects'
    if name == 'list_servers':
        return f'{len(result.get("servers", []))} servers'
    if name == 'start_timer':
        return f'timing {result.get("project", "")}'
    if name == 'stop_timer':
        return 'stopped'
    if name == 'get_active_timer':
        return result.get('elapsed', 'no timer') if result.get('running') else 'no timer'
    if name == 'write_memory':
        return 'saved'
    if name == 'delete_memory':
        return 'deleted' if result.get('deleted') else 'not found'
    if name == 'loyd':
        if 'text' in result:
            return f'{result.get("backend","?")} · {len(result["text"])} chars'
        return f'error: {result.get("error","?")[:50]}'
    return 'done'


def _ssh_run(user, server, command):
    import base64, io
    key_b64 = getattr(settings, 'SSH_PRIVATE_KEY_B64', '')
    if not key_b64:
        return {"error": "SSH_PRIVATE_KEY_B64 not configured in environment"}

    from apps.servers.models import Server as ServerModel
    srv = (
        ServerModel.objects.filter(owner=user, name__icontains=server).first()
        or ServerModel.objects.filter(owner=user, host__icontains=server).first()
    )
    if not srv:
        return {"error": f"No server matching '{server}' found"}

    try:
        import paramiko
        key_pem = base64.b64decode(key_b64).decode()
        pkey = None
        for KeyClass in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey, paramiko.DSSKey):
            try:
                pkey = KeyClass.from_private_key(io.StringIO(key_pem))
                break
            except Exception:
                continue
        if pkey is None:
            return {"error": "Could not parse SSH private key — check SSH_PRIVATE_KEY_B64"}

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(srv.host, port=srv.port, username=srv.ssh_user, pkey=pkey, timeout=15)
        _, stdout, stderr = client.exec_command(command, timeout=60)
        out = stdout.read().decode(errors='replace')
        err = stderr.read().decode(errors='replace')
        exit_code = stdout.channel.recv_exit_status()
        client.close()
        return {
            "server": srv.name,
            "host": srv.host,
            "command": command,
            "stdout": out,
            "stderr": err,
            "exit_code": exit_code,
        }
    except Exception as e:
        return {"error": str(e)}


def _search_files(user, query, path=".", case_sensitive=True):
    search_path = (WORKSPACE / path.lstrip("/")).resolve()
    if not str(search_path).startswith(str(WORKSPACE.resolve())):
        return {"error": "Path escapes workspace"}

    cmd = [
        "grep", "-rn",
        "--include=*.py", "--include=*.html", "--include=*.js",
        "--include=*.css", "--include=*.txt", "--include=*.yml",
        "--include=*.json", "--include=*.md", "--include=*.sh",
        "--exclude-dir=__pycache__", "--exclude-dir=.git",
        "--exclude-dir=migrations", "--exclude-dir=staticfiles",
    ]
    if not case_sensitive:
        cmd.append("-i")
    cmd += [query, str(search_path)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    lines = result.stdout.strip().splitlines()
    ws_prefix = str(WORKSPACE.resolve()) + "/"
    lines = [l.replace(ws_prefix, "") for l in lines]
    truncated = len(lines) > 200
    return {
        "query": query,
        "matches": len(lines),
        "truncated": truncated,
        "results": "\n".join(lines[:200]),
    }


def _git_status(user):
    result = subprocess.run(
        ["git", "status", "--short"], capture_output=True, text=True, cwd=str(WORKSPACE)
    )
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, cwd=str(WORKSPACE)
    )
    return {"branch": branch.stdout.strip(), "status": result.stdout or "(clean)"}


def _git_diff(user):
    stat = subprocess.run(
        ["git", "diff", "--stat"], capture_output=True, text=True, cwd=str(WORKSPACE)
    )
    diff = subprocess.run(
        ["git", "diff"], capture_output=True, text=True, cwd=str(WORKSPACE)
    )
    out = diff.stdout
    return {"stat": stat.stdout or "(no changes)", "diff": out[-8000:] if len(out) > 8000 else out}


def _git_commit(user, message):
    subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(WORKSPACE))
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True, text=True, cwd=str(WORKSPACE)
    )
    return {
        "returncode": result.returncode,
        "success": result.returncode == 0,
        "output": (result.stdout + result.stderr).strip(),
    }


def _docker_rebuild(user):
    compose_bin = "/usr/local/bin/docker-compose"
    compose_file = "/workspace/docker-compose.yml"

    result = subprocess.run(
        [compose_bin, "-p", "hihilabs", "-f", compose_file, "up", "-d", "--build"],
        capture_output=True, text=True, timeout=300, cwd="/workspace",
    )
    # Return last 60 lines of output — build logs are verbose
    out_lines = (result.stdout + result.stderr).strip().splitlines()
    return {
        "returncode": result.returncode,
        "success": result.returncode == 0,
        "output": "\n".join(out_lines[-60:]),
    }


def _loyd(user, prompt, context="", system="", tags=None, model="auto", max_tokens=2048):
    import time
    from apps.workers.models import Client, JobType, Job

    client, _ = Client.objects.get_or_create(
        slug="hihi-internal",
        defaults={"name": "HiHi Internal", "color": "#7c6af7"},
    )
    job_type, _ = JobType.objects.get_or_create(
        slug="ai_task",
        defaults={"label": "AI Task", "requires_gpu": False},
    )

    job = Job.objects.create(
        client=client,
        job_type=job_type,
        priority=10,
        label=prompt[:100],
        payload={
            "prompt": prompt,
            "context": context,
            "system": system,
            "tags": tags or [],
            "model": model,
            "max_tokens": max_tokens,
        },
    )

    deadline = time.time() + 90
    while time.time() < deadline:
        time.sleep(2)
        job.refresh_from_db()
        if job.status == "done":
            result = job.result or {}
            return {
                "text":    result.get("text", ""),
                "backend": result.get("backend", "unknown"),
                "model":   result.get("model", ""),
                "job_id":  job.pk,
            }
        if job.status == "error":
            return {"error": job.error or "Loyd job failed", "job_id": job.pk}

    return {"error": f"Loyd job #{job.pk} timed out after 90s — still {job.status}", "job_id": job.pk}


_HANDLERS = {
    "list_projects": _list_projects,
    "get_project": _get_project,
    "create_project": _create_project,
    "create_task": _create_task,
    "update_task": _update_task,
    "list_servers": _list_servers,
    "get_active_timer": _get_active_timer,
    "start_timer": _start_timer,
    "stop_timer": _stop_timer,
    "read_file": _read_file,
    "write_file": _write_file,
    "list_dir": _list_dir,
    "run_manage": _run_manage,
    "docker_rebuild": _docker_rebuild,
    "search_files": _search_files,
    "git_status": _git_status,
    "git_diff": _git_diff,
    "git_commit": _git_commit,
    "trigger_deploy": _trigger_deploy,
    "ssh_run": _ssh_run,
    "write_memory": _write_memory,
    "delete_memory": _delete_memory,
    "loyd": _loyd,
}

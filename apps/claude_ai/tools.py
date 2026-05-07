import json
import subprocess
from datetime import date
from pathlib import Path

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


_ALLOWED_MANAGE = {"migrate", "makemigrations", "showmigrations", "check", "diffsettings"}


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
}

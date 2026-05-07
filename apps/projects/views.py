import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Project, Task, TimeEntry


# ── Projects ──────────────────────────────────────────────────────────────────

@login_required
def project_index(request):
    projects = Project.objects.filter(owner=request.user).exclude(status='archived')
    running = TimeEntry.objects.filter(owner=request.user, ended_at__isnull=True).first()
    return render(request, 'projects/index.html', {
        'projects': projects,
        'running': running,
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    tasks = project.tasks.all()
    entries = project.time_entries.filter(ended_at__isnull=False)[:20]
    running = TimeEntry.objects.filter(owner=request.user, ended_at__isnull=True).first()
    return render(request, 'projects/detail.html', {
        'project': project,
        'tasks': tasks,
        'entries': entries,
        'running': running,
    })


@login_required
@require_POST
def project_create(request):
    data = json.loads(request.body)
    p = Project.objects.create(
        owner=request.user,
        name=data['name'],
        client=data.get('client', ''),
        color=data.get('color', '#7c6af7'),
        hourly_rate=data.get('hourly_rate', 150),
    )
    return JsonResponse({'ok': True, 'id': p.pk, 'url': f'/projects/{p.pk}/'})


@login_required
@require_POST
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    data = json.loads(request.body)
    for field in ['name', 'client', 'description', 'status', 'color', 'hourly_rate']:
        if field in data:
            setattr(project, field, data[field])
    project.save()
    return JsonResponse({'ok': True})


# ── Tasks ─────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def task_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    data = json.loads(request.body)
    task = Task.objects.create(
        project=project,
        title=data['title'],
        priority=data.get('priority', 'normal'),
    )
    return JsonResponse({'ok': True, 'id': task.pk, 'title': task.title, 'priority': task.priority})


@login_required
@require_POST
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    data = json.loads(request.body)
    for field in ['title', 'notes', 'status', 'priority', 'order']:
        if field in data:
            setattr(task, field, data[field])
    if data.get('status') == 'done' and not task.completed_at:
        task.completed_at = timezone.now()
    elif data.get('status') != 'done':
        task.completed_at = None
    task.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    task.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def task_suggest(request, pk):
    """Ask Claude for a next-step suggestion on this task."""
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    import anthropic
    from django.conf import settings

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = (
        f'Project: {task.project.name} (client: {task.project.client or "internal"})\n'
        f'Task: {task.title}\n'
        f'Notes: {task.notes or "(none)"}\n'
        f'Status: {task.status}\n\n'
        'Give me ONE concrete next action to move this task forward. '
        'Max 2 sentences. Be specific, no filler.'
    )
    msg = client.messages.create(
        model=settings.CLAUDE_CHAT_MODEL,
        max_tokens=150,
        messages=[{'role': 'user', 'content': prompt}],
    )
    suggestion = msg.content[0].text
    task.claude_suggestion = suggestion
    task.save(update_fields=['claude_suggestion'])
    return JsonResponse({'ok': True, 'suggestion': suggestion})


# ── Time Tracking ─────────────────────────────────────────────────────────────

@login_required
@require_POST
def timer_start(request):
    data = json.loads(request.body)
    project_id = data.get('project_id')
    task_id = data.get('task_id')
    description = data.get('description', '')

    # Stop any running timer first
    TimeEntry.objects.filter(owner=request.user, ended_at__isnull=True).update(ended_at=timezone.now())

    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    task = None
    if task_id:
        task = get_object_or_404(Task, pk=task_id, project=project)
        if task.status == 'todo':
            task.status = 'doing'
            task.save(update_fields=['status'])

    entry = TimeEntry.objects.create(
        owner=request.user,
        project=project,
        task=task,
        description=description,
        started_at=timezone.now(),
    )
    return JsonResponse({
        'ok': True,
        'entry_id': entry.pk,
        'project': project.name,
        'task': task.title if task else None,
        'started_at': entry.started_at.isoformat(),
    })


@login_required
@require_POST
def timer_stop(request):
    entry = TimeEntry.objects.filter(owner=request.user, ended_at__isnull=True).first()
    if not entry:
        return JsonResponse({'ok': False, 'error': 'no running timer'})
    entry.ended_at = timezone.now()
    data = json.loads(request.body) if request.body else {}
    if data.get('description'):
        entry.description = data['description']
    entry.save()
    return JsonResponse({
        'ok': True,
        'duration': entry.duration_display(),
        'project': entry.project.name,
    })


@login_required
def timer_status(request):
    entry = TimeEntry.objects.filter(owner=request.user, ended_at__isnull=True).first()
    if not entry:
        return JsonResponse({'running': False})
    elapsed = int((timezone.now() - entry.started_at).total_seconds())
    return JsonResponse({
        'running': True,
        'entry_id': entry.pk,
        'project_id': entry.project_id,
        'project': entry.project.name,
        'task': entry.task.title if entry.task else None,
        'elapsed_seconds': elapsed,
        'started_at': entry.started_at.isoformat(),
    })


@login_required
def time_log(request):
    entries = TimeEntry.objects.filter(owner=request.user, ended_at__isnull=False).select_related('project', 'task')[:50]
    unbilled = [e for e in entries if not e.billed]
    return render(request, 'projects/time_log.html', {
        'entries': entries,
        'unbilled': unbilled,
    })


@login_required
@require_POST
def time_entry_delete(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk, owner=request.user)
    entry.delete()
    return JsonResponse({'ok': True})

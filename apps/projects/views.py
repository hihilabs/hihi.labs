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
    from apps.sound.models import Track
    tracks = Track.objects.filter(project=project).order_by('-created_at')
    return render(request, 'projects/detail.html', {
        'project': project,
        'tasks': tasks,
        'entries': entries,
        'running': running,
        'tracks': tracks,
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


# ── Global Tasks ─────────────────────────────────────────────────────────────

@login_required
def global_tasks(request):
    status_filter = request.GET.get('status', '')
    projects = Project.objects.filter(owner=request.user).exclude(status='archived').prefetch_related('tasks')
    task_groups = []
    total = 0
    for p in projects:
        qs = p.tasks.all()
        if status_filter:
            qs = qs.filter(status=status_filter)
        tasks = list(qs)
        if tasks:
            task_groups.append({'project': p, 'tasks': tasks})
            total += len(tasks)
    from datetime import date
    return render(request, 'projects/tasks.html', {
        'task_groups': task_groups,
        'total': total,
        'status_filter': status_filter,
        'today': date.today(),
        'all_projects': Project.objects.filter(owner=request.user).exclude(status='archived'),
    })


# ── Value Board ───────────────────────────────────────────────────────────────

@login_required
def value_board(request):
    projects = Project.objects.filter(owner=request.user).exclude(status='archived')
    rows = []
    for p in projects:
        entries = list(p.time_entries.filter(ended_at__isnull=False))
        total_secs = sum(e.duration_seconds() for e in entries)
        unbilled_secs = sum(e.duration_seconds() for e in entries if not e.billed)
        total_hours = round(total_secs / 3600, 2)
        unbilled_hours = round(unbilled_secs / 3600, 2)
        rate = float(p.hourly_rate)
        unbilled_value = round(rate * unbilled_hours, 2)
        total_value = round(rate * total_hours, 2)

        # Task metrics
        tasks = list(p.tasks.all())
        tasks_total = len(tasks)
        tasks_done  = sum(1 for t in tasks if t.status == 'done')
        tasks_doing = sum(1 for t in tasks if t.status == 'doing')
        tasks_blocked = sum(1 for t in tasks if t.status == 'blocked')
        tasks_open  = tasks_total - tasks_done
        completion_pct = round(tasks_done / tasks_total * 100) if tasks_total > 0 else 0

        # Potential value: extrapolate total value when 100% done
        if completion_pct >= 5 and total_hours > 0:
            potential_value = round(total_value / (completion_pct / 100), 2)
        elif total_hours > 0:
            potential_value = None  # too early to extrapolate
        else:
            potential_value = None

        # ROI: value per hour
        roi_per_hour = round(total_value / total_hours, 2) if total_hours > 0 else 0

        # Priority urgency
        urgent_open = sum(1 for t in tasks if t.priority in ('high', 'urgent') and t.status != 'done')

        # Health signal
        if tasks_total == 0 and total_hours == 0:
            health = 'zombie'       # no activity at all
        elif total_hours >= 4 and completion_pct < 15:
            health = 'stalled'      # significant investment, almost no progress
        elif tasks_blocked > 0:
            health = 'blocked'
        elif urgent_open > 0:
            health = 'urgent'
        elif completion_pct >= 80:
            health = 'closing'      # almost done — push to finish
        elif completion_pct >= 40 or total_hours > 0:
            health = 'healthy'
        else:
            health = 'new'

        # Priority sort score: unbilled + urgency boost
        sort_score = unbilled_value + (urgent_open * 500) + (total_hours * rate * 0.1)

        rows.append({
            'project': p,
            'total_hours': total_hours,
            'unbilled_hours': unbilled_hours,
            'unbilled_value': unbilled_value,
            'total_value': total_value,
            'has_unbilled': unbilled_hours > 0,
            'tasks_total': tasks_total,
            'tasks_done': tasks_done,
            'tasks_doing': tasks_doing,
            'tasks_blocked': tasks_blocked,
            'tasks_open': tasks_open,
            'completion_pct': completion_pct,
            'potential_value': potential_value,
            'roi_per_hour': roi_per_hour,
            'urgent_open': urgent_open,
            'health': health,
            'sort_score': sort_score,
        })

    rows.sort(key=lambda r: r['sort_score'], reverse=True)
    total_unbilled = sum(r['unbilled_value'] for r in rows)
    total_potential = sum(r['potential_value'] for r in rows if r['potential_value'])
    return render(request, 'projects/value_board.html', {
        'rows': rows,
        'total_unbilled': round(total_unbilled, 2),
        'total_potential': round(total_potential, 2),
    })


@login_required
@require_POST
def draft_invoice(request, pk):
    from apps.billing.models import Invoice, InvoiceLine
    from datetime import date, timedelta

    project = get_object_or_404(Project, pk=pk, owner=request.user)
    unbilled = list(project.time_entries.filter(ended_at__isnull=False, billed=False))
    if not unbilled:
        return JsonResponse({'ok': False, 'error': 'No unbilled entries'}, status=400)

    client_name = ''
    client_email = ''
    if hasattr(project, 'client_ref') and project.client_ref:
        client_name = project.client_ref.name
        client_email = project.client_ref.email or ''
    elif project.client:
        client_name = project.client

    inv = Invoice.objects.create(
        owner=request.user,
        number=Invoice.next_number(request.user),
        client_name=client_name,
        client_email=client_email,
        status='draft',
        issued_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        notes=f'Time entries for {project.name}',
    )

    total_secs = sum(e.duration_seconds() for e in unbilled)
    total_hours = round(total_secs / 3600, 2)
    InvoiceLine.objects.create(
        invoice=inv,
        description=f'{project.name} — engineering services',
        quantity=total_hours,
        rate=project.hourly_rate,
        project=project,
        order=0,
    )

    # Mark entries as billed
    project.time_entries.filter(ended_at__isnull=False, billed=False).update(billed=True)

    from django.urls import reverse
    return JsonResponse({'ok': True, 'invoice_url': reverse('billing:detail', args=[inv.pk])})

import json
import hashlib
from datetime import date, timedelta, datetime

import requests
from icalendar import Calendar as ICalendar
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.projects.models import Project, Task, TimeEntry
from apps.billing.models import Invoice
from apps.clients.models import FollowUp
from apps.messaging.models import Notification
from .models import UserCalendarFeed, ProjectSubscription, QuickNote


# ── helpers ──────────────────────────────────────────────────────────────────

ENTITY_COLORS = {
    'binsky':    '#a78bfa',
    'fckry':     '#f472b6',
    'community': '#2dd4bf',
    'clients':   '#60a5fa',
    'general':   '#3a3a5a',
}


def _fetch_ics_events(feed: UserCalendarFeed, window_start: date, window_end: date) -> list:
    """Fetch and parse a single ICS feed, returning events in the 7-day window."""
    cache_key = f'ics_{hashlib.md5(feed.ics_url.encode()).hexdigest()}_{window_start}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(feed.ics_url, timeout=8)
        resp.raise_for_status()
        cal = ICalendar.from_ical(resp.content)
    except Exception:
        return []

    events = []
    for component in cal.walk():
        if component.name != 'VEVENT':
            continue
        try:
            dtstart = component.get('DTSTART')
            if not dtstart:
                continue
            val = dtstart.dt
            if isinstance(val, datetime):
                ev_date = val.date()
                ev_time = val.strftime('%H:%M')
                all_day = False
            else:
                ev_date = val
                ev_time = None
                all_day = True

            if not (window_start <= ev_date <= window_end):
                continue

            summary = str(component.get('SUMMARY', ''))
            location = str(component.get('LOCATION', ''))

            events.append({
                'date':     ev_date.isoformat(),
                'time':     ev_time,
                'all_day':  all_day,
                'title':    summary,
                'location': location,
                'color':    feed.color,
                'calendar': feed.name,
            })
        except Exception:
            continue

    events.sort(key=lambda e: (e['date'], e['time'] or '99:99'))
    cache.set(cache_key, events, 300)  # 5-minute cache
    return events


# ── main dashboard ────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    now         = timezone.now()
    today       = now.date()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # KPI stats (same as before — owned projects)
    _proj_base = Project.objects.all() if request.user.is_superuser else Project.objects.filter(owner=request.user)
    active_project_count = _proj_base.filter(status='active').count()

    _task_filter = {'project__status': 'active'} if request.user.is_superuser else {
        'project__owner': request.user, 'project__status': 'active'
    }
    open_tasks_all = Task.objects.filter(**_task_filter).exclude(status='done').count()

    running = TimeEntry.objects.filter(
        owner=request.user, ended_at__isnull=True
    ).select_related('project', 'task').first()

    month_entries = TimeEntry.objects.filter(
        owner=request.user, started_at__gte=month_start, ended_at__isnull=False
    )
    month_hours = round(sum(e.duration_seconds() for e in month_entries) / 3600, 1)

    unbilled_entries = TimeEntry.objects.filter(
        owner=request.user, ended_at__isnull=False, billed=False
    ).select_related('project')
    unbilled_hours = round(sum(e.duration_seconds() for e in unbilled_entries) / 3600, 1)
    unbilled_value = round(sum(
        (e.duration_seconds() / 3600) * float(e.project.hourly_rate)
        for e in unbilled_entries
    ), 2)

    draft_count = Invoice.objects.filter(owner=request.user, status='draft').count()
    sent_count  = Invoice.objects.filter(owner=request.user, status='sent').count()

    due_followups = list(
        FollowUp.objects.filter(owner=request.user, done=False, due_date__lte=today)
        .select_related('client').order_by('due_date')[:5]
    )
    alerts = list(
        Notification.objects.filter(user=request.user, read=False).order_by('-created_at')[:6]
    )

    calendar_feeds = list(UserCalendarFeed.objects.filter(user=request.user, is_active=True))
    grabbed_ids    = set(
        ProjectSubscription.objects.filter(user=request.user).values_list('project_id', flat=True)
    )
    notes = list(QuickNote.objects.filter(user=request.user)[:10])

    # All projects visible to this user (owned + grabbed) for task module
    all_visible_projects = list(
        _proj_base.filter(status='active').order_by('entity', 'name')[:60]
    )

    feed_palette = ['#a78bfa','#f472b6','#2dd4bf','#60a5fa','#4ade80','#fbbf24','#f87171','#7c6af7']

    return render(request, 'dashboard/dashboard.html', {
        'active_project_count': active_project_count,
        'feed_palette':         feed_palette,
        'open_tasks':           open_tasks_all,
        'running':              running,
        'month_hours':          month_hours,
        'unbilled_hours':       unbilled_hours,
        'unbilled_value':       unbilled_value,
        'draft_count':          draft_count,
        'sent_count':           sent_count,
        'due_followups':        due_followups,
        'alerts':               alerts,
        'calendar_feeds':       calendar_feeds,
        'grabbed_ids':          grabbed_ids,
        'notes':                notes,
        'all_visible_projects': all_visible_projects,
        'entity_colors':        ENTITY_COLORS,
        'today':                today,
    })


# ── module: calendar ──────────────────────────────────────────────────────────

@login_required
def module_calendar(request):
    today      = date.today()
    window_end = today + timedelta(days=6)

    feeds  = UserCalendarFeed.objects.filter(user=request.user, is_active=True)
    events = []
    for feed in feeds:
        events.extend(_fetch_ics_events(feed, today, window_end))

    # Group by date
    days = []
    for i in range(7):
        d = today + timedelta(days=i)
        day_events = sorted(
            [e for e in events if e['date'] == d.isoformat()],
            key=lambda e: (e['all_day'], e['time'] or '00:00'),
        )
        days.append({'date': d, 'events': day_events, 'label': _day_label(d, today)})

    cal_filter = request.GET.get('cal', 'all')
    all_calendars = sorted({e['calendar']: e['color'] for e in events}.items())

    return render(request, 'dashboard/modules/calendar.html', {
        'days':          days,
        'cal_filter':    cal_filter,
        'all_calendars': all_calendars,
        'total_events':  len(events),
    })


def _day_label(d: date, today: date) -> str:
    diff = (d - today).days
    if diff == 0:   return 'today'
    if diff == 1:   return 'tomorrow'
    return d.strftime('%A').lower()


# ── module: tasks ─────────────────────────────────────────────────────────────

@login_required
def module_tasks(request):
    today       = date.today()
    entity_filter = request.GET.get('entity', 'all')

    grabbed_ids = set(
        ProjectSubscription.objects.filter(user=request.user).values_list('project_id', flat=True)
    )
    proj_q = Q(owner=request.user) | Q(id__in=grabbed_ids)
    projects = Project.objects.filter(proj_q, status='active').order_by('entity', '-updated_at')
    if entity_filter != 'all':
        projects = projects.filter(entity=entity_filter)

    proj_ids = list(projects.values_list('id', flat=True))
    tasks = (
        Task.objects
        .filter(project_id__in=proj_ids)
        .exclude(status='done')
        .select_related('project')
        .order_by('project__entity', 'project_id', 'order', 'due_date')
    )

    # Group by project
    groups = {}
    proj_map = {p.id: p for p in projects}
    for t in tasks:
        pid = t.project_id
        if pid not in groups:
            p = proj_map.get(pid, t.project)
            groups[pid] = {
                'project':  p,
                'entity':   p.entity,
                'color':    p.color,
                'ec':       ENTITY_COLORS.get(p.entity, '#3a3a5a'),
                'tasks':    [],
                'grabbed':  pid in grabbed_ids,
            }
        due = t.due_date
        overdue = due and due < today
        groups[pid]['tasks'].append({
            'id':      t.id,
            'title':   t.title,
            'status':  t.status,
            'overdue': overdue,
            'today':   due == today if due else False,
            'due':     due.isoformat() if due else None,
            'notes':   t.notes,
        })

    # Add-task project selector (all visible projects regardless of entity filter)
    all_grabbed_ids = grabbed_ids
    all_projects_qs = Project.objects.filter(
        Q(owner=request.user) | Q(id__in=all_grabbed_ids), status='active'
    ).order_by('entity', 'name')

    return render(request, 'dashboard/modules/tasks.html', {
        'groups':         list(groups.values()),
        'entity_filter':  entity_filter,
        'entity_colors':  ENTITY_COLORS,
        'today':          today,
        'all_projects':   all_projects_qs,
    })


# ── module: notes ─────────────────────────────────────────────────────────────

@login_required
def module_notes(request):
    notes = QuickNote.objects.filter(user=request.user)[:15]
    return render(request, 'dashboard/modules/notes.html', {'notes': notes})


# ── module: digest (Lloyd) ────────────────────────────────────────────────────

@login_required
def module_digest(request):
    today = date.today()
    grabbed_ids = set(
        ProjectSubscription.objects.filter(user=request.user).values_list('project_id', flat=True)
    )
    proj_q = Q(owner=request.user) | Q(id__in=grabbed_ids)

    overdue_tasks = list(
        Task.objects.filter(proj_q, due_date__lt=today)
        .exclude(status='done')
        .select_related('project')
        .order_by('due_date')[:10]
    )
    open_invoices = list(
        Invoice.objects.filter(owner=request.user)
        .exclude(status__in=['paid', 'void'])
        .order_by('due_date')[:5]
    )
    followups = list(
        FollowUp.objects.filter(owner=request.user, done=False, due_date__lte=today)
        .select_related('client')[:5]
    )

    total_open = Task.objects.filter(proj_q).exclude(status='done').count()

    # Lloyd summary via Claude
    lloyd_summary = None
    if settings.ANTHROPIC_API_KEY and not request.GET.get('skip_ai'):
        cache_key = f'lloyd_digest_{request.user.id}_{today}'
        lloyd_summary = cache.get(cache_key)
        if not lloyd_summary:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                context_lines = [f'Today is {today}. Open tasks: {total_open}.']
                if overdue_tasks:
                    context_lines.append('Overdue tasks: ' + ', '.join(f'{t.title} ({t.project.name})' for t in overdue_tasks))
                if open_invoices:
                    context_lines.append('Open invoices: ' + ', '.join(f'#{i.pk} ${i.amount}' for i in open_invoices))
                if followups:
                    context_lines.append('Due follow-ups: ' + ', '.join(f'{f.client.display_name} — {f.note}' for f in followups))
                msg = client.messages.create(
                    model=settings.CLAUDE_SMART_MODEL,
                    max_tokens=200,
                    system=(
                        'You are Lloyd, a sharp internal assistant for a freelance creative agency. '
                        'Give a 2–3 sentence morning briefing: what needs attention today, '
                        'biggest risk, one concrete suggestion. Be direct, no fluff.'
                    ),
                    messages=[{'role': 'user', 'content': '\n'.join(context_lines)}],
                )
                lloyd_summary = msg.content[0].text
                cache.set(cache_key, lloyd_summary, 3600)  # fresh once per hour
            except Exception:
                pass

    return render(request, 'dashboard/modules/digest.html', {
        'overdue_tasks':  overdue_tasks,
        'open_invoices':  open_invoices,
        'followups':      followups,
        'total_open':     total_open,
        'lloyd_summary':  lloyd_summary,
        'today':          today,
    })


# ── note actions ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def add_note(request):
    data    = json.loads(request.body)
    content = data.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'empty'}, status=400)
    note = QuickNote.objects.create(user=request.user, content=content)
    return JsonResponse({'id': note.id, 'content': note.content})


@login_required
@require_POST
def delete_note(request, pk):
    QuickNote.objects.filter(user=request.user, pk=pk).delete()
    return JsonResponse({'ok': True})


# ── task actions ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def mark_task_done(request):
    data = json.loads(request.body)
    tid  = data.get('id')
    grabbed_ids = set(
        ProjectSubscription.objects.filter(user=request.user).values_list('project_id', flat=True)
    )
    task = get_object_or_404(
        Task,
        pk=tid,
        project__in=Project.objects.filter(Q(owner=request.user) | Q(id__in=grabbed_ids))
    )
    task.status       = 'done'
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def add_task(request):
    data    = json.loads(request.body)
    title   = data.get('title', '').strip()
    proj_id = data.get('project_id')
    if not title:
        return JsonResponse({'error': 'empty'}, status=400)

    grabbed_ids = set(
        ProjectSubscription.objects.filter(user=request.user).values_list('project_id', flat=True)
    )
    project = get_object_or_404(
        Project,
        pk=proj_id,
        **({'owner': request.user} if not proj_id in grabbed_ids else {})
    ) if proj_id else None

    if not project:
        # create a task without a project — attach to first owned active project or skip
        return JsonResponse({'error': 'project required'}, status=400)

    task = Task.objects.create(project=project, title=title)
    return JsonResponse({
        'id':      task.id,
        'title':   task.title,
        'proj_id': project.id,
        'entity':  project.entity,
        'color':   project.color,
    })


# ── grab project ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def grab_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    sub, created = ProjectSubscription.objects.get_or_create(user=request.user, project=project)
    if not created:
        sub.delete()
        return JsonResponse({'grabbed': False})
    return JsonResponse({'grabbed': True})


# ── calendar feed management ──────────────────────────────────────────────────

@login_required
@require_POST
def calendar_feed_add(request):
    data  = json.loads(request.body)
    name  = data.get('name', '').strip()
    url   = data.get('url', '').strip()
    color = data.get('color', '#7c6af7').strip()
    if not name or not url:
        return JsonResponse({'error': 'name and url required'}, status=400)
    feed, _ = UserCalendarFeed.objects.update_or_create(
        user=request.user, name=name,
        defaults={'ics_url': url, 'color': color, 'is_active': True},
    )
    return JsonResponse({'id': feed.id, 'name': feed.name, 'color': feed.color})


@login_required
@require_POST
def calendar_feed_delete(request, pk):
    UserCalendarFeed.objects.filter(user=request.user, pk=pk).delete()
    return JsonResponse({'ok': True})


@login_required
def calendar_feeds_list(request):
    feeds = list(UserCalendarFeed.objects.filter(user=request.user))
    return render(request, 'dashboard/modules/calendar_feeds.html', {'feeds': feeds})

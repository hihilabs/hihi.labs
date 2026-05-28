import json
from django.http import JsonResponse, FileResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control
from django.shortcuts import render
from django.conf import settings


@cache_control(max_age=0, no_cache=True, no_store=True)
def service_worker(request):
    import os
    path = os.path.join(settings.BASE_DIR, "static", "sw.js")
    resp = FileResponse(open(path, "rb"), content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    return resp


def offline(request):
    return render(request, "offline.html")


@login_required
def push_vapid_key(request):
    return JsonResponse({"key": settings.VAPID_PUBLIC_KEY_B64})


@login_required
@require_POST
def push_subscribe(request):
    from apps.core.models import PushSubscription
    try:
        data   = json.loads(request.body)
        keys   = data.get("keys", {})
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"],
            defaults={
                "user":       request.user,
                "p256dh":     keys.get("p256dh", ""),
                "auth":       keys.get("auth", ""),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
            },
        )
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid"}, status=400)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def push_unsubscribe(request):
    from apps.core.models import PushSubscription
    try:
        data = json.loads(request.body)
        PushSubscription.objects.filter(endpoint=data["endpoint"]).delete()
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid"}, status=400)
    return JsonResponse({"ok": True})



@login_required
def power_search(request):
    from django.db.models import Q
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 2:
        return JsonResponse({'results': []})
    results = []
    try:
        from apps.projects.models import Project, Task
        for p in Project.objects.filter(owner=request.user).filter(
            Q(name__icontains=q) | Q(client__icontains=q)
        )[:6]:
            results.append({'type': 'project', 'label': p.name,
                             'sub': p.client or '', 'url': f'/projects/{p.pk}/', 'color': p.color})
        for task in Task.objects.filter(project__owner=request.user,
            title__icontains=q).select_related('project')[:5]:
            results.append({'type': 'task', 'label': task.title,
                             'sub': task.project.name, 'url': f'/projects/{task.project.pk}/', 'color': ''})
    except Exception:
        pass
    try:
        from apps.clients.models import Client
        for c in Client.objects.filter(owner=request.user).filter(
            Q(name__icontains=q) | Q(company__icontains=q) | Q(email__icontains=q)
        )[:4]:
            results.append({'type': 'client', 'label': c.name,
                             'sub': c.company or c.email or '', 'url': f'/clients/{c.pk}/', 'color': ''})
    except Exception:
        pass
    try:
        from apps.proposals.models import Proposal
        for p in Proposal.objects.filter(owner=request.user, title__icontains=q)[:3]:
            results.append({'type': 'proposal', 'label': p.title,
                             'sub': p.client.name if p.client else '', 'url': f'/proposals/{p.pk}/', 'color': ''})
    except Exception:
        pass
    try:
        from apps.sound.models import Track
        from django.db.models import Q as Qs
        for tr in Track.objects.filter(owner=request.user).filter(
            Qs(title__icontains=q) | Qs(tags__icontains=q)
        )[:4]:
            results.append({'type': 'track', 'label': tr.title,
                             'sub': tr.project.name if tr.project else '', 'url': f'/sound/{tr.pk}/', 'color': ''})
    except Exception:
        pass
    return JsonResponse({'results': results[:15]})


@login_required
def dashboard(request):
    from apps.projects.models import Project, TimeEntry
    from apps.billing.models import Invoice
    from django.utils import timezone

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    from apps.projects.models import Task
    from django.db.models import Count, Q

    # Superusers see all projects; regular users see only their own
    _proj_base = Project.objects.all() if request.user.is_superuser else Project.objects.filter(owner=request.user)

    active_project_count = _proj_base.filter(status='active').count()

    _task_filter = {'project__status': 'active'} if request.user.is_superuser else {'project__owner': request.user, 'project__status': 'active'}
    open_tasks_all = Task.objects.filter(**_task_filter).exclude(status='done').count()

    active_projects = list(
        _proj_base.filter(status='active')
        .prefetch_related('tasks', 'time_entries')
        .order_by('-updated_at')[:12]
    )

    running = TimeEntry.objects.filter(
        owner=request.user, ended_at__isnull=True
    ).select_related('project', 'task').first()

    month_entries = TimeEntry.objects.filter(
        owner=request.user, started_at__gte=month_start, ended_at__isnull=False
    ).select_related('project')

    month_hours = round(sum(e.duration_seconds() for e in month_entries) / 3600, 1)

    unbilled_entries = TimeEntry.objects.filter(
        owner=request.user, ended_at__isnull=False, billed=False
    ).select_related('project')
    unbilled_hours = round(sum(e.duration_seconds() for e in unbilled_entries) / 3600, 1)
    unbilled_value = sum(
        (e.duration_seconds() / 3600) * float(e.project.hourly_rate)
        for e in unbilled_entries
    )

    draft_count = Invoice.objects.filter(owner=request.user, status='draft').count()
    sent_count  = Invoice.objects.filter(owner=request.user, status='sent').count()

    recent_entries = TimeEntry.objects.filter(
        owner=request.user, ended_at__isnull=False
    ).select_related('project', 'task').order_by('-started_at')[:10]

    from apps.servers.models import Server
    from apps.messaging.models import Notification
    from apps.clients.models import FollowUp
    import datetime

    servers = list(Server.objects.filter(owner=request.user)[:8])
    alerts  = list(Notification.objects.filter(user=request.user, read=False).order_by('-created_at')[:6])
    today   = now.date()
    due_followups = list(
        FollowUp.objects.filter(owner=request.user, done=False, due_date__lte=today)
        .select_related('client').order_by('due_date')[:5]
    )

    return render(request, 'dashboard.html', {
        'active_project_count': active_project_count,
        'active_projects': active_projects,
        'open_tasks': open_tasks_all,
        'running': running,
        'month_hours': month_hours,
        'unbilled_hours': unbilled_hours,
        'unbilled_value': round(unbilled_value, 2),
        'draft_count': draft_count,
        'sent_count': sent_count,
        'recent_entries': recent_entries,
        'servers': servers,
        'alerts': alerts,
        'due_followups': due_followups,
        'today': today,
    })

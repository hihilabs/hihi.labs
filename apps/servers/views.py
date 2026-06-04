import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .models import Server
from apps.core.superuser import su_qs, su_get


@login_required
def index(request):
    servers = su_qs(request.user, Server.objects)
    # Group by platform for the fleet view
    order = ['vps', 'docker', 'unraid', 'local', 'external']
    groups = {}
    for s in servers:
        groups.setdefault(s.platform, []).append(s)
    platform_groups = [
        (p, dict(Server.PLATFORMS).get(p, p), groups[p])
        for p in order if p in groups
    ]
    return render(request, 'servers/index.html', {
        'servers': servers,
        'platform_groups': platform_groups,
        'icons': Server.ICONS,
        'platforms': Server.PLATFORMS,
        'service_types': Server.SERVICE_TYPES,
    })


@login_required
@require_POST
def server_add(request):
    data = json.loads(request.body)
    s = Server.objects.create(
        owner=request.user,
        name=data.get('name', '').strip(),
        host=data.get('host', '').strip(),
        ssh_user=data.get('ssh_user', 'root').strip(),
        port=int(data.get('port', 22)),
        tags=data.get('tags', '').strip(),
        notes=data.get('notes', '').strip(),
        icon=data.get('icon', 'fa-server'),
        color=data.get('color', '#7c6af7'),
        domain=data.get('domain', '').strip(),
        git_repo=data.get('git_repo', '').strip(),
        platform=data.get('platform', 'vps'),
        service_type=data.get('service_type', 'ssh'),
        status_url=data.get('status_url', '').strip(),
    )
    return JsonResponse({'id': s.pk, 'name': s.name})


@login_required
@require_POST
def server_delete(request, pk):
    su_get(Server, pk, request.user).delete()
    return JsonResponse({'ok': True})


@login_required
def server_ping(request, pk):
    server = su_get(Server, pk, request.user)
    up = _check_service(server)
    return JsonResponse({'up': up, 'id': server.pk})


@login_required
def fleet_status(request):
    """Bulk health check — returns {id: bool} for all services."""
    servers = su_qs(request.user, Server.objects)
    result = {}
    for s in servers:
        result[s.pk] = _check_service(s)
    return JsonResponse(result)


def _check_service(server):
    """HTTP check if status_url set, else TCP check on ssh port."""
    if server.status_url:
        try:
            import urllib.request
            req = urllib.request.Request(server.status_url, method='GET')
            with urllib.request.urlopen(req, timeout=4) as resp:
                return resp.status < 500
        except Exception:
            return False
    elif server.domain:
        try:
            import urllib.request
            req = urllib.request.Request(server.domain, method='GET')
            with urllib.request.urlopen(req, timeout=4) as resp:
                return resp.status < 500
        except Exception:
            return False
    else:
        import socket as _socket
        try:
            s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            s.settimeout(3)
            result = s.connect_ex((server.host, server.port))
            s.close()
            return result == 0
        except Exception:
            return False


# ── Session check-in / check-out ─────────────────────────────────────────────

@login_required
def sessions_index(request):
    from .models import Developer, WorkSession
    from django.utils import timezone
    active = WorkSession.objects.filter(status__in=['active', 'idle']).select_related('developer', 'server')
    recent = WorkSession.objects.filter(status='checked_out').select_related('developer', 'server')[:20]
    devs   = Developer.objects.filter(is_active=True)
    servers = su_qs(request.user, Server.objects)
    return render(request, 'servers/sessions.html', {
        'active_sessions': active,
        'recent_sessions': recent,
        'developers': devs,
        'servers': servers,
    })


@login_required
@require_POST
def session_checkin(request):
    from .models import Developer, WorkSession
    data = json.loads(request.body)
    dev_id  = data.get('developer_id')
    task    = data.get('task_summary', '').strip()
    project = data.get('project_name', '').strip()
    srv_id  = data.get('server_id')
    try:
        dev = Developer.objects.get(pk=dev_id)
    except Developer.DoesNotExist:
        return JsonResponse({'error': 'Unknown developer'}, status=400)
    server = Server.objects.filter(pk=srv_id).first() if srv_id else None
    # Close any existing open session for this dev
    WorkSession.objects.filter(developer=dev, status__in=['active', 'idle']).update(
        status='checked_out',
        checked_out_at=__import__('django.utils.timezone', fromlist=['timezone']).timezone.now(),
    )
    session = WorkSession.objects.create(
        developer=dev, server=server,
        project_name=project, task_summary=task,
        client_ip=request.META.get('REMOTE_ADDR'),
    )
    return JsonResponse({'ok': True, 'session_id': session.pk, 'token': session.session_token,
                         'message': f'✓ {dev.display_name} checked in'})


@login_required
@require_POST
def session_checkout(request):
    from .models import WorkSession
    from django.utils import timezone
    data = json.loads(request.body)
    pk   = data.get('session_id')
    note = data.get('note', '').strip()
    try:
        s = WorkSession.objects.get(pk=pk)
    except WorkSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    if note:
        s.task_summary = (s.task_summary + '\n\n' + note).strip()
    s.status = 'checked_out'
    s.checked_out_at = timezone.now()
    s.save()
    return JsonResponse({'ok': True, 'duration': s.duration_display()})


@login_required
@require_POST
def session_heartbeat(request):
    from .models import WorkSession
    data = json.loads(request.body)
    WorkSession.objects.filter(pk=data.get('session_id')).update(
        status=data.get('status', 'active')
    )
    return JsonResponse({'ok': True})


# ── Terminal hook API — no browser auth, uses session_token ──────────────────

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_greet(request):
    """
    Called by the VPS login hook (PAM / MOTD script).
    Receives SSH fingerprint + IP, returns a Lloyd greeting + identity guess.
    POST: {fingerprint, ip, hostname}
    """
    from .models import Developer, WorkSession
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    data = json.loads(request.body) if request.body else {}
    fingerprint = data.get('fingerprint', '')
    ip          = data.get('ip', request.META.get('REMOTE_ADDR', ''))
    hostname    = data.get('hostname', '')

    # Try to identify by SSH key fingerprint
    dev = None
    if fingerprint:
        from django.db.models import Q
        for d in Developer.objects.filter(is_active=True):
            if fingerprint in d.fingerprint_list():
                dev = d
                break

    if dev:
        greeting = (
            f"👋 Hey {dev.avatar_emoji} {dev.display_name}! Welcome back.\n"
            f"Connected from {ip or 'unknown'}\n"
            f"Remember to check in at https://hihilabs.xyz/servers/sessions/ "
            f"before starting work."
        )
        return JsonResponse({
            'identified': True,
            'developer': dev.display_name,
            'developer_id': dev.pk,
            'greeting': greeting,
        })
    else:
        greeting = (
            "👋 Hi there! I'm Lloyd.\n"
            "I don't recognize this device yet.\n"
            f"Connecting from: {ip or 'unknown'}\n\n"
            "Who is this? Please check in at:\n"
            "  https://hihilabs.xyz/servers/sessions/\n\n"
            "Or run:  hh-checkin  in your terminal."
        )
        return JsonResponse({
            'identified': False,
            'greeting': greeting,
            'fingerprint': fingerprint,
            'register_url': 'https://hihilabs.xyz/servers/sessions/',
        })


@csrf_exempt
def api_identify(request):
    """Register a new SSH fingerprint for a developer. Requires session_token from an active session."""
    from .models import Developer, WorkSession
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    data = json.loads(request.body)
    token       = data.get('session_token', '')
    fingerprint = data.get('fingerprint', '')
    session = WorkSession.objects.filter(session_token=token, status='active').select_related('developer').first()
    if not session:
        return JsonResponse({'error': 'Invalid or expired session token'}, status=401)
    dev = session.developer
    existing = dev.fingerprint_list()
    if fingerprint and fingerprint not in existing:
        dev.ssh_key_fingerprints = '\n'.join(existing + [fingerprint])
        dev.save(update_fields=['ssh_key_fingerprints'])
    return JsonResponse({'ok': True, 'developer': dev.display_name,
                         'message': f'Device registered for {dev.display_name}'})

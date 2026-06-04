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

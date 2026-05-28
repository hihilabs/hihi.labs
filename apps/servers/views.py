import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from .models import Server
from apps.core.superuser import su_qs, su_get


@login_required
def index(request):
    servers = su_qs(request.user, Server.objects)
    return render(request, 'servers/index.html', {
        'servers': servers,
        'icons': Server.ICONS,
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
    )
    return JsonResponse({
        'id': s.pk, 'name': s.name, 'host': s.host,
        'ssh_url': s.ssh_url(), 'ssh_command': s.ssh_command(),
    })


@login_required
@require_POST
def server_delete(request, pk):
    su_get(Server, pk, request.user).delete()
    return JsonResponse({'ok': True})


@login_required
def server_ping(request, pk):
    import socket as _socket
    server = su_get(Server, pk, request.user)
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((server.host, server.port))
        s.close()
        up = result == 0
    except Exception:
        up = False
    return JsonResponse({'up': up, 'host': server.host, 'name': server.name})

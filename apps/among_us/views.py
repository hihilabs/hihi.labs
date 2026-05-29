import re
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from .models import GameServer


def index(request):
    server = GameServer.objects.filter(active=True).first()
    return render(request, 'among_us/index.html', {'server': server})


def download_cfg(request):
    ip = request.GET.get('ip', '').strip()
    port = request.GET.get('port', '22023').strip()
    name = request.GET.get('name', 'Custom Server').strip()[:50]

    if not ip or not re.match(r'^[\d.]+$', ip):
        return HttpResponseBadRequest('Valid IPv4 address required')
    try:
        port = max(1, min(65535, int(port)))
    except (ValueError, TypeError):
        port = 22023

    response = HttpResponse(_make_cfg(name, ip, port), content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="daemon.unify.cfg"'
    return response


def download_family_cfg(request):
    server = GameServer.objects.filter(active=True).first()
    if not server:
        return HttpResponseBadRequest('No family server configured yet.')
    response = HttpResponse(_make_cfg(server.name, server.ip, server.port), content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="daemon.unify.cfg"'
    return response


def _make_cfg(name, ip, port):
    return (
        '[General]\n\n'
        '## Show default regions alongside custom ones.\n'
        '# Setting type: Boolean\n'
        '# Default value: false\n'
        'ShowVanillaRegions = false\n\n'
        '[Region 1]\n\n'
        '## Display name shown in the region selector.\n'
        '# Setting type: String\n'
        '# Default value: \n'
        f'Name = {name}\n\n'
        '## IP address of the custom server.\n'
        '# Setting type: String\n'
        '# Default value: \n'
        f'IP = {ip}\n\n'
        '## Port number of the custom server.\n'
        '# Setting type: Int32\n'
        '# Default value: 22023\n'
        f'Port = {port}\n'
    )

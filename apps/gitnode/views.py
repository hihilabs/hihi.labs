import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from . import ssh
from .models import ManagedRepo


@staff_member_required
def index(request):
    repos = ManagedRepo.objects.filter(active=True).select_related('server')
    return render(request, 'gitnode/index.html', {'repos': repos})


@staff_member_required
def repo_status(request, pk):
    repo = get_object_or_404(ManagedRepo, pk=pk)
    status = ssh.git_status(repo.server, repo.path)
    log    = ssh.git_log(repo.server, repo.path)
    branch = ssh.git_branch(repo.server, repo.path)
    clean  = status == ''
    return JsonResponse({
        'ok': True,
        'clean': clean,
        'status': status or '✓ clean',
        'log': log,
        'branch': branch,
    })


@staff_member_required
@require_POST
def repo_scoop(request, pk):
    repo = get_object_or_404(ManagedRepo, pk=pk)
    data = json.loads(request.body) if request.body else {}
    msg  = data.get('message', '').strip() or f'scoop: {repo.name} checkpoint'
    ok, out = ssh.scoop(repo.server, repo.path, msg)
    return JsonResponse({'ok': ok, 'output': out})


@staff_member_required
@require_POST
def repo_deploy(request, pk):
    repo = get_object_or_404(ManagedRepo, pk=pk)
    ok, out = ssh.deploy(repo.server, repo.path, repo.service_name)
    return JsonResponse({'ok': ok, 'output': out})


@staff_member_required
@require_POST
def scoop_all(request):
    data = json.loads(request.body) if request.body else {}
    msg  = data.get('message', '').strip() or 'scoop: all-repos checkpoint'
    repos   = ManagedRepo.objects.filter(active=True).select_related('server')
    results = []
    for repo in repos:
        ok, out = ssh.scoop(repo.server, repo.path, msg)
        results.append({'name': repo.name, 'ok': ok, 'output': out})
    return JsonResponse({'ok': True, 'results': results})

import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Whiteboard


@login_required
def index(request):
    boards = Whiteboard.objects.filter(owner=request.user)
    from apps.projects.models import Project
    projects = Project.objects.filter(owner=request.user).exclude(status='archived')
    return render(request, 'whiteboards/index.html', {'boards': boards, 'projects': projects})


@login_required
def detail(request, pk):
    board = get_object_or_404(Whiteboard, pk=pk, owner=request.user)
    return render(request, 'whiteboards/canvas.html', {'board': board})


@login_required
@require_POST
def create(request):
    data = json.loads(request.body)
    title = data.get('title', 'Untitled').strip() or 'Untitled'
    project_id = data.get('project_id') or None
    board = Whiteboard.objects.create(owner=request.user, title=title, project_id=project_id)
    return JsonResponse({'ok': True, 'id': board.pk})


@login_required
@require_POST
def save(request, pk):
    board = get_object_or_404(Whiteboard, pk=pk, owner=request.user)
    data = json.loads(request.body)
    board.data = json.dumps(data.get('canvas', {}))
    if 'title' in data:
        board.title = data['title'].strip() or board.title
    board.save(update_fields=['data', 'title', 'updated_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Whiteboard, pk=pk, owner=request.user).delete()
    return JsonResponse({'ok': True})

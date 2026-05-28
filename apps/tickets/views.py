import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Ticket, TicketComment
from apps.projects.models import Project


def _ticket_qs(user):
    if user.is_superuser:
        return Ticket.objects.select_related('project', 'reporter')
    return Ticket.objects.filter(reporter=user).select_related('project', 'reporter')


@login_required
def index(request):
    status_filter = request.GET.get('status', '')
    qs = _ticket_qs(request.user)
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'tickets/index.html', {
        'tickets': qs,
        'status_filter': status_filter,
        'open_count': _ticket_qs(request.user).filter(status='open').count(),
    })


@login_required
def detail(request, pk):
    if request.user.is_superuser:
        ticket = get_object_or_404(Ticket, pk=pk)
    else:
        ticket = get_object_or_404(Ticket, pk=pk, reporter=request.user)
    comments = ticket.comments.select_related('author')
    return render(request, 'tickets/detail.html', {
        'ticket': ticket,
        'comments': comments,
    })


@login_required
@require_POST
def create(request):
    data = json.loads(request.body)
    project_id = data.get('project_id')
    project = None
    if project_id:
        if request.user.is_superuser:
            project = get_object_or_404(Project, pk=project_id)
        else:
            project = get_object_or_404(Project, pk=project_id, owner=request.user)
    ticket = Ticket.objects.create(
        reporter=request.user,
        project=project,
        title=data['title'],
        body=data.get('body', ''),
        type=data.get('type', 'request'),
        priority=data.get('priority', 'normal'),
    )
    return JsonResponse({'ok': True, 'id': ticket.pk})


@login_required
@require_POST
def update(request, pk):
    if request.user.is_superuser:
        ticket = get_object_or_404(Ticket, pk=pk)
    else:
        ticket = get_object_or_404(Ticket, pk=pk, reporter=request.user)
    data = json.loads(request.body)
    for field in ['title', 'body', 'status', 'type', 'priority']:
        if field in data:
            setattr(ticket, field, data[field])
    ticket.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def delete(request, pk):
    if request.user.is_superuser:
        ticket = get_object_or_404(Ticket, pk=pk)
    else:
        ticket = get_object_or_404(Ticket, pk=pk, reporter=request.user)
    ticket.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def comment_add(request, pk):
    if request.user.is_superuser:
        ticket = get_object_or_404(Ticket, pk=pk)
    else:
        ticket = get_object_or_404(Ticket, pk=pk, reporter=request.user)
    data = json.loads(request.body)
    body = data.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'empty'}, status=400)
    c = TicketComment.objects.create(ticket=ticket, author=request.user, body=body)
    return JsonResponse({'ok': True, 'id': c.pk, 'author': request.user.get_full_name() or request.user.username})

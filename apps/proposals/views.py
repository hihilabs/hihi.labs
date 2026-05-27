import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.urls import reverse
from .models import Proposal, ProposalLine


@login_required
def index(request):
    proposals = Proposal.objects.filter(owner=request.user).select_related('client', 'project').order_by('-created_at')
    try:
        from apps.clients.models import Client
        all_clients = Client.objects.filter(owner=request.user).order_by('name')
    except Exception:
        all_clients = []
    return render(request, 'proposals/index.html', {'proposals': proposals, 'all_clients': all_clients})


@login_required
def detail(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk, owner=request.user)
    try:
        from apps.clients.models import Client
        clients = Client.objects.filter(owner=request.user).order_by('name')
    except Exception:
        clients = []
    try:
        from apps.projects.models import Project
        projects = Project.objects.filter(owner=request.user).exclude(status='archived').order_by('name')
    except Exception:
        projects = []
    return render(request, 'proposals/detail.html', {
        'proposal': proposal, 'clients': clients, 'projects': projects,
    })


@login_required
@require_POST
def create(request):
    data = json.loads(request.body)
    proposal = Proposal.objects.create(
        owner=request.user,
        number=Proposal.next_number(request.user),
        title=data.get('title', 'New Proposal').strip(),
        client_id=data.get('client_id') or None,
        project_id=data.get('project_id') or None,
    )
    return JsonResponse({'ok': True, 'redirect': reverse('proposals:detail', args=[proposal.pk])})


@login_required
@require_POST
def update(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk, owner=request.user)
    data = json.loads(request.body)
    for field in ['title', 'status', 'intro', 'notes', 'valid_until']:
        if field in data:
            setattr(proposal, field, data[field] or None if field == 'valid_until' else data[field])
    if 'client_id' in data:
        proposal.client_id = data['client_id'] or None
    if 'project_id' in data:
        proposal.project_id = data['project_id'] or None
    if 'tax_rate' in data:
        proposal.tax_rate = float(data['tax_rate'] or 0)
    proposal.save()
    return JsonResponse({'ok': True, 'subtotal': float(proposal.subtotal),
                          'tax': float(proposal.tax_amount), 'total': float(proposal.total)})


@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Proposal, pk=pk, owner=request.user).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def line_save(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk, owner=request.user)
    data = json.loads(request.body)
    proposal.lines.all().delete()
    for i, line in enumerate(data.get('lines', [])):
        ProposalLine.objects.create(
            proposal=proposal,
            description=line.get('description', ''),
            quantity=line.get('quantity', 1),
            rate=line.get('rate', 0),
            order=i,
        )
    proposal.save(update_fields=['updated_at'])
    return JsonResponse({'ok': True, 'subtotal': float(proposal.subtotal),
                          'tax': float(proposal.tax_amount), 'total': float(proposal.total)})

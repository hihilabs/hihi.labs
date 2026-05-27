import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.urls import reverse
from .models import Contract


@login_required
def index(request):
    contracts = Contract.objects.filter(owner=request.user).select_related('client', 'project').order_by('-created_at')
    try:
        from apps.clients.models import Client
        all_clients = Client.objects.filter(owner=request.user).order_by('name')
    except Exception:
        all_clients = []
    return render(request, 'contracts/index.html', {'contracts': contracts, 'all_clients': all_clients})


@login_required
def detail(request, pk):
    contract = get_object_or_404(Contract, pk=pk, owner=request.user)
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
    return render(request, 'contracts/detail.html', {
        'contract': contract, 'clients': clients, 'projects': projects,
    })


@login_required
@require_POST
def create(request):
    data = json.loads(request.body)
    contract = Contract.objects.create(
        owner=request.user,
        number=Contract.next_number(request.user),
        title=data.get('title', 'New Contract').strip(),
        client_id=data.get('client_id') or None,
        project_id=data.get('project_id') or None,
    )
    return JsonResponse({'ok': True, 'redirect': reverse('contracts:detail', args=[contract.pk])})


@login_required
@require_POST
def update(request, pk):
    contract = get_object_or_404(Contract, pk=pk, owner=request.user)
    data = json.loads(request.body)
    for field in ['title', 'status', 'body', 'signed_by']:
        if field in data:
            setattr(contract, field, data[field])
    for datefield in ['start_date', 'end_date']:
        if datefield in data:
            setattr(contract, datefield, data[datefield] or None)
    if 'client_id' in data:
        contract.client_id = data['client_id'] or None
    if 'project_id' in data:
        contract.project_id = data['project_id'] or None
    if 'value' in data:
        contract.value = float(data['value'] or 0)
    contract.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Contract, pk=pk, owner=request.user).delete()
    return JsonResponse({'ok': True})

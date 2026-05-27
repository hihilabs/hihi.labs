import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import Client, Contact, HostingSubscription


@login_required
def index(request):
    status = request.GET.get('status', '')
    qs = Client.objects.filter(owner=request.user)
    if status:
        qs = qs.filter(status=status)
    return render(request, 'clients/index.html', {'clients': qs, 'status_filter': status})


@login_required
def detail(request, pk):
    client = get_object_or_404(Client, pk=pk, owner=request.user)
    contacts = client.contacts.all()
    hosting  = client.hosting_subscriptions.all()
    proposals = []
    contracts = []
    files = []
    try:
        from apps.proposals.models import Proposal
        proposals = Proposal.objects.filter(client=client).order_by('-created_at')
    except Exception:
        pass
    try:
        from apps.contracts.models import Contract
        contracts = Contract.objects.filter(client=client).order_by('-created_at')
    except Exception:
        pass
    return render(request, 'clients/detail.html', {
        'client': client, 'contacts': contacts,
        'hosting': hosting, 'proposals': proposals, 'contracts': contracts,
    })


@login_required
@require_POST
def create(request):
    data = json.loads(request.body)
    client = Client.objects.create(
        owner=request.user,
        name=data.get('name', '').strip(),
        company=data.get('company', '').strip(),
        email=data.get('email', '').strip(),
        phone=data.get('phone', '').strip(),
        status=data.get('status', 'active'),
    )
    from django.urls import reverse
    return JsonResponse({'ok': True, 'id': client.pk, 'redirect': reverse('clients:detail', args=[client.pk])})


@login_required
@require_POST
def update(request, pk):
    client = get_object_or_404(Client, pk=pk, owner=request.user)
    data = json.loads(request.body)
    for field in ['name', 'company', 'email', 'phone', 'website', 'address',
                   'city', 'state', 'country', 'notes', 'color', 'status', 'hosted_domain']:
        if field in data:
            setattr(client, field, data[field])
    client.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Client, pk=pk, owner=request.user).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def contact_create(request, pk):
    client = get_object_or_404(Client, pk=pk, owner=request.user)
    data = json.loads(request.body)
    c = Contact.objects.create(
        client=client, owner=request.user,
        first_name=data.get('first_name', '').strip(),
        last_name=data.get('last_name', '').strip(),
        email=data.get('email', '').strip(),
        phone=data.get('phone', '').strip(),
        role=data.get('role', '').strip(),
        is_primary=data.get('is_primary', False),
    )
    return JsonResponse({'ok': True, 'id': c.pk, 'name': c.full_name})


@login_required
@require_POST
def contact_delete(request, pk, contact_pk):
    contact = get_object_or_404(Contact, pk=contact_pk, client__owner=request.user)
    contact.delete()
    return JsonResponse({'ok': True})

import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Client, Contact, HostingSubscription, FollowUp


STATUS_COLS = [
    ('lead',     'Lead',     '#f59e0b'),
    ('active',   'Active',   '#10b981'),
    ('inactive', 'Inactive', '#6b7280'),
    ('archived', 'Archived', '#4b5563'),
]

@login_required
def index(request):
    qs = Client.objects.filter(owner=request.user).prefetch_related('contacts', 'projects')
    grouped = {
        'lead':     list(qs.filter(status='lead')),
        'active':   list(qs.filter(status='active')),
        'inactive': list(qs.filter(status='inactive')),
        'archived': list(qs.filter(status='archived')),
    }
    return render(request, 'clients/index.html', {
        'clients': qs, 'grouped': grouped, 'status_cols': STATUS_COLS,
    })


@login_required
def detail(request, pk):
    client = get_object_or_404(Client, pk=pk, owner=request.user)
    contacts  = client.contacts.all()
    hosting   = client.hosting_subscriptions.all()
    followups = client.followups.filter(owner=request.user)
    projects  = client.projects.filter(owner=request.user).order_by('-updated_at')

    proposals, contracts, invoices, threads = [], [], [], []
    try:
        from apps.proposals.models import Proposal
        proposals = list(Proposal.objects.filter(client=client).order_by('-created_at'))
    except Exception:
        pass
    try:
        from apps.contracts.models import Contract
        contracts = list(Contract.objects.filter(client=client).order_by('-created_at'))
    except Exception:
        pass
    try:
        from apps.billing.models import Invoice
        invoices = list(Invoice.objects.filter(client_fk=client, owner=request.user).order_by('-created_at'))
    except Exception:
        pass
    try:
        from apps.messaging.models import Thread
        threads = list(Thread.objects.filter(client=client).order_by('-updated_at')[:10])
    except Exception:
        pass

    # Build activity timeline (newest first)
    timeline = []
    for p in proposals:
        timeline.append({'date': p.created_at, 'type': 'proposal', 'label': f'Proposal: {p.title}',
                         'status': p.status, 'url': f'/proposals/{p.pk}/', 'icon': 'fa-file-pen', 'color': 'var(--accent)'})
    for c in contracts:
        timeline.append({'date': c.created_at, 'type': 'contract', 'label': f'Contract: {c.title}',
                         'status': c.status, 'url': f'/contracts/{c.pk}/', 'icon': 'fa-file-signature', 'color': 'var(--teal)'})
    for inv in invoices:
        timeline.append({'date': inv.created_at, 'type': 'invoice', 'label': f'{inv.number}',
                         'status': inv.status, 'url': f'/billing/{inv.pk}/', 'icon': 'fa-file-invoice-dollar', 'color': 'var(--yellow)'})
    for proj in projects:
        timeline.append({'date': proj.created_at, 'type': 'project', 'label': f'Project: {proj.name}',
                         'status': proj.status, 'url': f'/projects/{proj.pk}/', 'icon': 'fa-folder-open', 'color': proj.color})
    for t in threads:
        timeline.append({'date': t.created_at, 'type': 'thread', 'label': t.subject or f'Thread #{t.pk}',
                         'status': t.source, 'url': f'/messaging/thread/{t.pk}/', 'icon': 'fa-comments', 'color': 'var(--green)'})
    timeline.sort(key=lambda x: x['date'], reverse=True)

    edit_fields = [
        ('name',    'Name',    client.name),
        ('company', 'Company', client.company),
        ('email',   'Email',   client.email),
        ('phone',   'Phone',   client.phone),
        ('website', 'Website', client.website),
        ('address', 'Address', client.address),
        ('city',    'City',    client.city),
        ('state',   'State',   client.state),
        ('country', 'Country', client.country),
    ]
    return render(request, 'clients/detail.html', {
        'client': client, 'contacts': contacts,
        'hosting': hosting, 'proposals': proposals, 'contracts': contracts,
        'invoices': invoices, 'projects': projects, 'threads': threads,
        'followups': followups, 'timeline': timeline,
        'edit_fields': edit_fields,
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


@login_required
@require_POST
def followup_create(request, pk):
    client = get_object_or_404(Client, pk=pk, owner=request.user)
    data = json.loads(request.body)
    note = data.get('note', '').strip()
    if not note:
        return JsonResponse({'ok': False, 'error': 'note required'}, status=400)
    fu = FollowUp.objects.create(
        client=client, owner=request.user,
        note=note,
        due_date=data.get('due_date') or None,
        priority=data.get('priority', 'normal'),
    )
    return JsonResponse({'ok': True, 'id': fu.pk,
                         'note': fu.note, 'due_date': str(fu.due_date) if fu.due_date else '',
                         'priority': fu.priority, 'done': fu.done})


@login_required
@require_POST
def followup_update(request, pk, fu_pk):
    fu = get_object_or_404(FollowUp, pk=fu_pk, client__owner=request.user)
    data = json.loads(request.body)
    if 'done' in data:
        fu.done = data['done']
        fu.done_at = timezone.now() if data['done'] else None
    if 'note' in data:
        fu.note = data['note']
    if 'due_date' in data:
        fu.due_date = data['due_date'] or None
    fu.save()
    return JsonResponse({'ok': True, 'done': fu.done})


@login_required
@require_POST
def followup_delete(request, pk, fu_pk):
    get_object_or_404(FollowUp, pk=fu_pk, client__owner=request.user).delete()
    return JsonResponse({'ok': True})

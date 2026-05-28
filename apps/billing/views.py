import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.projects.models import Project, TimeEntry
from .models import Invoice, InvoiceLine
from apps.core.superuser import su_qs, su_get


@login_required
def index(request):
    invoices = su_qs(request.user, Invoice.objects).prefetch_related('lines')
    outstanding = sum(inv.total for inv in invoices if inv.status in ('draft', 'sent'))
    paid_total = sum(inv.total for inv in invoices if inv.status == 'paid')
    projects = su_qs(request.user, Project.objects).filter(status='active')
    unbilled_projects = [p for p in projects if p.unbilled_hours() > 0]
    return render(request, 'billing/index.html', {
        'invoices': invoices,
        'outstanding': outstanding,
        'paid_total': paid_total,
        'unbilled_projects': unbilled_projects,
    })


@login_required
def invoice_new(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        client_name = data.get('client_name', '').strip()
        client_email = data.get('client_email', '').strip()
        notes = data.get('notes', '').strip()
        project_ids = data.get('project_ids', [])
        due_days = int(data.get('due_days', 14))

        inv = Invoice.objects.create(
            owner=request.user,
            number=Invoice.next_number(request.user),
            client_name=client_name,
            client_email=client_email,
            notes=notes,
            due_date=date.today() + timedelta(days=due_days),
        )

        for pid in project_ids:
            try:
                project = su_get(Project, pid, request.user)
            except Project.DoesNotExist:
                continue
            entries = project.time_entries.filter(ended_at__isnull=False, billed=False)
            hours = round(sum(e.duration_seconds() for e in entries) / 3600, 2)
            if hours > 0:
                InvoiceLine.objects.create(
                    invoice=inv,
                    description=f'{project.name} — development services',
                    quantity=hours,
                    rate=project.hourly_rate,
                    project=project,
                    order=InvoiceLine.objects.filter(invoice=inv).count(),
                )

        # manual lines
        for line in data.get('manual_lines', []):
            InvoiceLine.objects.create(
                invoice=inv,
                description=line.get('description', ''),
                quantity=line.get('quantity', 1),
                rate=line.get('rate', 0),
                order=InvoiceLine.objects.filter(invoice=inv).count(),
            )

        return JsonResponse({'id': inv.pk})

    projects = su_qs(request.user, Project.objects).filter(status='active')
    return render(request, 'billing/invoice_new.html', {
        'projects': projects,
        'next_number': Invoice.next_number(request.user),
    })


@login_required
def invoice_detail(request, pk):
    inv = su_get(Invoice, pk, request.user)
    return render(request, 'billing/invoice_detail.html', {'invoice': inv})


@login_required
@require_POST
def invoice_add_line(request, pk):
    inv = su_get(Invoice, pk, request.user)
    data = json.loads(request.body)
    line = InvoiceLine.objects.create(
        invoice=inv,
        description=data.get('description', ''),
        quantity=data.get('quantity', 1),
        rate=data.get('rate', 0),
        order=inv.lines.count(),
    )
    return JsonResponse({'id': line.pk, 'amount': float(line.amount)})


@login_required
@require_POST
def invoice_delete_line(request, pk, line_pk):
    inv = su_get(Invoice, pk, request.user)
    InvoiceLine.objects.filter(pk=line_pk, invoice=inv).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def invoice_mark_sent(request, pk):
    inv = su_get(Invoice, pk, request.user)
    inv.status = 'sent'
    inv.save(update_fields=['status', 'updated_at'])
    return JsonResponse({'status': inv.status})


@login_required
@require_POST
def invoice_mark_paid(request, pk):
    inv = su_get(Invoice, pk, request.user)
    inv.status = 'paid'
    inv.save(update_fields=['status', 'updated_at'])
    # mark all linked time entries as billed
    project_ids = inv.lines.filter(project__isnull=False).values_list('project_id', flat=True)
    TimeEntry.objects.filter(
        project_id__in=project_ids, billed=False, ended_at__isnull=False,
    ).update(billed=True)
    return JsonResponse({'status': inv.status})


@login_required
@require_POST
def invoice_void(request, pk):
    inv = su_get(Invoice, pk, request.user)
    inv.status = 'void'
    inv.save(update_fields=['status', 'updated_at'])
    return JsonResponse({'status': inv.status})


@login_required
@require_POST
def invoice_delete(request, pk):
    inv = su_get(Invoice, pk, request.user)
    if inv.status == 'paid':
        return JsonResponse({'error': 'Cannot delete a paid invoice'}, status=400)
    inv.delete()
    return JsonResponse({'ok': True})

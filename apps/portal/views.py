import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import ClientPortalConfig, SiteFooter
from apps.clients.models import Client


@staff_member_required
def admin_view(request):
    clients = Client.objects.all().order_by('name')
    configs = {c.client_id: c for c in ClientPortalConfig.objects.select_related('client')}
    public_footer = SiteFooter.get('public')
    portal_footer = SiteFooter.get('portal')
    return render(request, 'portal/admin.html', {
        'clients':       clients,
        'configs':       configs,
        'public_footer': public_footer,
        'portal_footer': portal_footer,
    })


@staff_member_required
@require_POST
def client_config_save(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    data = json.loads(request.body)
    cfg, _ = ClientPortalConfig.objects.get_or_create(client=client)
    for field in ['show_projects', 'show_invoices', 'show_files', 'show_tickets', 'show_messages']:
        if field in data:
            setattr(cfg, field, bool(data[field]))
    if 'welcome_message' in data:
        cfg.welcome_message = data['welcome_message'].strip()
    if 'accent_color' in data:
        cfg.accent_color = data['accent_color']
    cfg.save()
    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def footer_save(request, footer_type):
    if footer_type not in ('public', 'portal'):
        return JsonResponse({'error': 'invalid type'}, status=400)
    data = json.loads(request.body)
    footer = SiteFooter.get(footer_type)
    if 'html_content' in data:
        footer.html_content = data['html_content']
    if 'show_ticket_form' in data:
        footer.show_ticket_form = bool(data['show_ticket_form'])
    if 'ticket_form_title' in data:
        footer.ticket_form_title = data['ticket_form_title'].strip() or 'Submit a Ticket'
    footer.save()
    return JsonResponse({'ok': True})


def ticket_submit(request):
    """Public (no auth required) ticket submission from footer form."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from apps.tickets.models import Ticket
    data = json.loads(request.body)
    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title required'}, status=400)
    ticket = Ticket.objects.create(
        title=title,
        body=data.get('body', '').strip(),
        submitter_name=data.get('name', '').strip(),
        submitter_email=data.get('email', '').strip(),
        reporter=request.user if request.user.is_authenticated else None,
        type=data.get('type', 'request'),
        priority='normal',
    )
    return JsonResponse({'ok': True, 'id': ticket.pk})

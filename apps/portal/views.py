import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .models import ClientPortalConfig, SiteFooter
from apps.clients.models import Client


# ── Staff admin ────────────────────────────────────────────────────────────────

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
        'theme_choices': ClientPortalConfig.THEMES,
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
    if 'portal_theme' in data and data['portal_theme'] in dict(ClientPortalConfig.THEMES):
        cfg.portal_theme = data['portal_theme']
    cfg.save()
    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def regenerate_token(request, client_pk):
    """Staff: rotate the portal token (old URL stops working immediately)."""
    import uuid
    client = get_object_or_404(Client, pk=client_pk)
    client.portal_token = uuid.uuid4()
    client.save(update_fields=['portal_token'])
    return JsonResponse({'ok': True, 'token': str(client.portal_token)})


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
    """Public ticket submission from footer form."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from apps.tickets.models import Ticket
    data = json.loads(request.body)

    # Honeypot — bots fill this in, real users never see it
    if data.get('_hp', '').strip():
        return JsonResponse({'ok': True})  # silently discard

    title = data.get('title', '').strip()[:300]
    if not title:
        return JsonResponse({'error': 'Title required'}, status=400)

    ticket = Ticket.objects.create(
        title=title,
        body=data.get('body', '').strip()[:4000],
        submitter_name=data.get('name', '').strip()[:100],
        submitter_email=data.get('email', '').strip()[:200],
        reporter=request.user if request.user.is_authenticated else None,
        type=data.get('type', 'request'),
        priority='normal',
    )
    return JsonResponse({'ok': True, 'id': ticket.pk})


# ── Client-facing portal ───────────────────────────────────────────────────────

def _portal_context(client, is_preview=False):
    """Build context for both the token portal and staff preview."""
    cfg = getattr(client, 'portal_config', None)
    portal_footer = SiteFooter.get('portal')

    projects = []
    if cfg is None or cfg.show_projects:
        try:
            from apps.projects.models import Project, Task
            qs = (client.projects
                        .exclude(status='archived')
                        .order_by('-updated_at')[:20])
            for p in qs:
                total = Task.objects.filter(project=p).count()
                done  = Task.objects.filter(project=p, status='done').count()
                projects.append({
                    'pk':         p.pk,
                    'name':       p.name,
                    'status':     p.status,
                    'stage':      p.stage,
                    'color':      p.color,
                    'description': p.description,
                    'task_total': total,
                    'task_done':  done,
                    'task_pct':   round(done / total * 100) if total else 0,
                    'open_tasks': total - done,
                })
        except Exception:
            projects = []

    accent = (cfg.accent_color if cfg else None) or client.color or '#7c6af7'
    theme  = (cfg.portal_theme  if cfg else None) or 'default'

    display   = client.company or client.name or ''
    initials  = ''.join(w[0] for w in display.split()[:2]).upper() or '?'

    return {
        'client':          client,
        'cfg':             cfg,
        'projects':        projects,
        'notifications':   [],   # future: client-visible notification queryset
        'portal_footer':   portal_footer,
        'accent':          accent,
        'theme':           theme,
        'is_preview':      is_preview,
        'avatar_initials': initials,
        'show_projects':   cfg.show_projects  if cfg else True,
        'show_invoices':   cfg.show_invoices  if cfg else True,
        'show_files':      cfg.show_files     if cfg else True,
        'show_tickets':    cfg.show_tickets   if cfg else True,
        'show_messages':   cfg.show_messages  if cfg else False,
        'welcome':         cfg.welcome_message if cfg else '',
    }


_SAFE_THEMES = {t[0] for t in ClientPortalConfig.THEMES}

_PORTAL_HEADERS = {
    # Prevent the token in the URL from leaking via Referer to external sites
    'Referrer-Policy':        'no-referrer',
    # Don't allow the portal to be embedded in an iframe (clickjacking)
    'X-Frame-Options':        'DENY',
    'X-Content-Type-Options': 'nosniff',
    # Allow inline styles/scripts (we use them) but block external script sources
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    ),
}


def _apply_portal_headers(response):
    for k, v in _PORTAL_HEADERS.items():
        response[k] = v
    return response


def client_portal(request, token):
    """Public client portal — no login required, accessed via token URL."""
    client = get_object_or_404(Client, portal_token=token)
    ctx = _portal_context(client, is_preview=False)
    theme = ctx['theme'] if ctx['theme'] in _SAFE_THEMES else 'default'
    return _apply_portal_headers(render(request, f'portal/themes/{theme}.html', ctx))


@staff_member_required
def portal_preview(request, client_pk):
    """Staff preview — same render as client, plus preview banner."""
    client = get_object_or_404(Client, pk=client_pk)
    ctx = _portal_context(client, is_preview=True)
    theme = ctx['theme'] if ctx['theme'] in _SAFE_THEMES else 'default'
    return _apply_portal_headers(render(request, f'portal/themes/{theme}.html', ctx))

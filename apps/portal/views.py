import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .models import ClientPortalConfig, SiteFooter
from apps.clients.models import Client, Contact


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

    if 'linked_clients' in data:
        ids = [int(pk) for pk in data['linked_clients'] if int(pk) != client.pk]
        client.portal_linked_clients.set(Client.objects.filter(pk__in=ids))

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
            client_ids = [client.pk] + list(client.portal_linked_clients.values_list('pk', flat=True))
            qs = (Project.objects
                        .filter(client_fk_id__in=client_ids)
                        .exclude(status='archived')
                        .order_by('-updated_at')[:30])
            for p in qs:
                total = Task.objects.filter(project=p).count()
                done  = Task.objects.filter(project=p, status='done').count()
                visible_tasks = []
                for t in (Task.objects.filter(project=p, client_visible=True)
                              .select_related('assigned_to_user', 'assigned_to_contact')
                              .order_by('order', 'created_at')):
                    assignee_name = None
                    assignee_type = None
                    if t.assigned_to_contact_id:
                        assignee_name = t.assigned_to_contact.full_name
                        assignee_type = 'contact'
                    elif t.assigned_to_user_id:
                        assignee_name = t.assigned_to_user.get_full_name() or t.assigned_to_user.username
                        assignee_type = 'team'
                    visible_tasks.append({
                        'pk':            t.pk,
                        'title':         t.title,
                        'status':        t.status,
                        'status_label':  t.get_status_display(),
                        'priority':      t.priority,
                        'due_date':      t.due_date,
                        'assignee_name': assignee_name,
                        'assignee_type': assignee_type,
                        'assignee_contact_id': t.assigned_to_contact_id,
                    })
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
                    'org':        p.client_fk.display_name if p.client_fk_id != client.pk else None,
                    'tasks':      visible_tasks,
                })
        except Exception:
            projects = []

    invoices = []
    if cfg is None or cfg.show_invoices:
        try:
            from apps.billing.models import Invoice
            client_ids = [client.pk] + list(client.portal_linked_clients.values_list('pk', flat=True))
            for inv in (Invoice.objects
                            .filter(client_fk_id__in=client_ids)
                            .exclude(status='draft')
                            .order_by('-issued_date')[:30]):
                invoices.append({
                    'number':      inv.number,
                    'status':      inv.status,
                    'status_label':inv.get_status_display(),
                    'issued_date': inv.issued_date,
                    'due_date':    inv.due_date,
                    'total':       inv.total,
                    'org':         inv.client_fk.display_name if inv.client_fk_id != client.pk else None,
                })
        except Exception:
            invoices = []

    files = []
    if cfg is None or cfg.show_files:
        try:
            from apps.files.models import ClientFile
            client_ids = [client.pk] + list(client.portal_linked_clients.values_list('pk', flat=True))
            for cf in (ClientFile.objects
                            .filter(client_id__in=client_ids)
                            .order_by('-created_at')[:50]):
                if cf.source == 'drive':
                    url = cf.drive_web_view_link
                elif cf.file:
                    url = cf.file.url
                else:
                    url = ''
                files.append({
                    'name':        cf.name,
                    'description': cf.description,
                    'url':         url,
                    'is_image':    cf.is_image,
                    'ext':         cf.ext,
                    'source':      cf.source,
                    'size':        cf.size,
                    'created_at':  cf.created_at,
                    'org':         cf.client.display_name if cf.client_id != client.pk else None,
                })
        except Exception:
            files = []

    threads = []
    if cfg is None or cfg.show_messages:
        try:
            from apps.messaging.models import Thread
            client_ids = [client.pk] + list(client.portal_linked_clients.values_list('pk', flat=True))
            for t in Thread.objects.filter(client_id__in=client_ids).order_by('-updated_at')[:30]:
                last = t.messages.filter(is_internal=False).order_by('-sent_at').first()
                threads.append({
                    'pk':       t.pk,
                    'subject':  t.subject or 'Conversation',
                    'last_body': (last.body[:140] if last else ''),
                    'last_at':   last.sent_at if last else t.created_at,
                    'count':     t.messages.filter(is_internal=False).count(),
                    'org':       t.client.display_name if t.client_id != client.pk else None,
                })
        except Exception:
            threads = []

    client_contacts = []
    try:
        from apps.clients.models import Contact
        client_ids = [client.pk] + list(client.portal_linked_clients.values_list('pk', flat=True))
        for c in Contact.objects.filter(client_id__in=client_ids).order_by('-is_primary', 'first_name'):
            client_contacts.append({'pk': c.pk, 'name': c.full_name, 'role': c.role})
    except Exception:
        client_contacts = []

    accent = (cfg.accent_color if cfg else None) or client.color or '#7c6af7'
    theme  = (cfg.portal_theme  if cfg else None) or 'default'

    display   = client.company or client.name or ''
    initials  = ''.join(w[0] for w in display.split()[:2]).upper() or '?'

    return {
        'client':          client,
        'cfg':             cfg,
        'projects':        projects,
        'invoices':        invoices,
        'files':           files,
        'threads':         threads,
        'client_contacts': client_contacts,
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


# ── Client invite email ────────────────────────────────────────────────────────

@staff_member_required
@require_POST
def send_invite(request, client_pk):
    from django.core.mail import send_mail
    from django.conf import settings as _s

    client = get_object_or_404(Client, pk=client_pk)
    data   = json.loads(request.body)
    to     = data.get('email', '').strip() or client.email

    if not to:
        return JsonResponse({'error': 'No email address'}, status=400)

    portal_url = f'{request.scheme}://{request.get_host()}/portal/view/{client.portal_token}/'
    owner_name = getattr(_s, 'SITE_OWNER', 'Andrew')
    site_name  = getattr(_s, 'SITE_NAME',  'HiHi Labs')

    subject = f'Your {site_name} portal is ready'
    body    = (
        f'Hi {client.name},\n\n'
        f'{owner_name} has set up your private client portal. '
        f'Use the link below to view your projects, files, invoices, and submit support requests:\n\n'
        f'{portal_url}\n\n'
        f'Keep this link private — it gives direct access to your portal with no password required.\n\n'
        f'— {owner_name} @ {site_name}'
    )

    try:
        send_mail(subject, body, _s.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    # Persist email on client if not already set
    if not client.email and to != client.email:
        client.email = to
        client.save(update_fields=['email'])

    return JsonResponse({'ok': True, 'sent_to': to})


# ── Portal voice transcribe (token-gated, no login) ───────────────────────────

def portal_voice_transcribe(request, token):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    client = get_object_or_404(Client, portal_token=token)

    from django.conf import settings as _s
    import tempfile, os

    if not _s.OPENAI_API_KEY:
        return JsonResponse({'error': 'Transcription not available'}, status=503)

    audio = request.FILES.get('audio')
    if not audio:
        return JsonResponse({'error': 'No audio'}, status=400)

    import openai
    oa = openai.OpenAI(api_key=_s.OPENAI_API_KEY)

    suffix = '.webm'
    if audio.name and '.' in audio.name:
        suffix = '.' + audio.name.rsplit('.', 1)[-1]

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        for chunk in audio.chunks():
            f.write(chunk)
        tmp = f.name

    try:
        with open(tmp, 'rb') as f:
            result = oa.audio.transcriptions.create(
                model=_s.WHISPER_MODEL,
                file=f,
                response_format='text',
            )
        transcript = result.strip()
    finally:
        os.unlink(tmp)

    return JsonResponse({'ok': True, 'transcript': transcript})


# ── Client portal messaging (token-gated, no login) ────────────────────────────

def _portal_system_user():
    from django.contrib.auth.models import User
    user, created = User.objects.get_or_create(
        username='portal-client',
        defaults={'first_name': 'Client', 'last_name': 'Portal', 'is_active': False},
    )
    if created:
        user.set_unusable_password()
        user.save()
    return user


def _client_thread_ids(client):
    client_ids = [client.pk] + list(client.portal_linked_clients.values_list('pk', flat=True))
    return client_ids


@require_POST
def portal_thread_new(request, token):
    from django.contrib.auth.models import User
    from apps.messaging.models import Thread, Message
    from apps.messaging.utils import notify

    client = get_object_or_404(Client, portal_token=token)
    data = json.loads(request.body)
    subject = (data.get('subject') or '').strip()[:500]
    body = (data.get('body') or '').strip()
    if not body:
        return JsonResponse({'error': 'Message required'}, status=400)

    sender = _portal_system_user()
    thread = Thread.objects.create(
        subject=subject or f'Message from {client.display_name}',
        client=client, source='internal', created_by=sender,
    )
    staff = User.objects.filter(is_staff=True, is_active=True)
    thread.participants.set(staff)

    msg = Message.objects.create(
        thread=thread, sender=sender, body=body,
        from_email=client.email or '',
    )

    for s in staff:
        notify(s, 'message', f'New message from {client.display_name}',
               body=body[:100], link=f'/messaging/thread/{thread.pk}/')

    return JsonResponse({
        'thread_pk': thread.pk,
        'subject': thread.subject,
        'message': {
            'id': msg.pk,
            'body': msg.body,
            'mine': True,
            'sender': client.display_name,
            'sent_at': msg.sent_at.strftime('%b %-d, %-I:%M %p'),
        },
    })


def portal_thread_detail(request, token, thread_pk):
    from apps.messaging.models import Thread

    client = get_object_or_404(Client, portal_token=token)
    thread = get_object_or_404(Thread, pk=thread_pk, client_id__in=_client_thread_ids(client))

    msgs = []
    for m in thread.messages.filter(is_internal=False).order_by('sent_at'):
        mine = (m.sender.username == 'portal-client')
        msgs.append({
            'id': m.pk,
            'body': m.body,
            'mine': mine,
            'sender': client.display_name if mine else (m.sender.get_short_name() or 'HiHi Labs'),
            'sent_at': m.sent_at.strftime('%b %-d, %-I:%M %p'),
        })

    return JsonResponse({'thread_pk': thread.pk, 'subject': thread.subject, 'messages': msgs})


@require_POST
def portal_thread_reply(request, token, thread_pk):
    from django.contrib.auth.models import User
    from apps.messaging.models import Thread, Message
    from apps.messaging.utils import notify

    client = get_object_or_404(Client, portal_token=token)
    thread = get_object_or_404(Thread, pk=thread_pk, client_id__in=_client_thread_ids(client))

    data = json.loads(request.body)
    body = (data.get('body') or '').strip()
    if not body:
        return JsonResponse({'error': 'Message required'}, status=400)

    sender = _portal_system_user()
    msg = Message.objects.create(
        thread=thread, sender=sender, body=body,
        from_email=client.email or '',
    )
    thread.save()  # bump updated_at

    for s in thread.participants.filter(is_staff=True, is_active=True):
        notify(s, 'message', f'Re: {thread.subject or "message"}',
               body=body[:100], link=f'/messaging/thread/{thread.pk}/')

    return JsonResponse({
        'id': msg.pk,
        'body': msg.body,
        'mine': True,
        'sender': client.display_name,
        'sent_at': msg.sent_at.strftime('%b %-d, %-I:%M %p'),
    })


@require_POST
def portal_task_assign(request, token, task_pk):
    """Let a portal client (re)assign a client_visible task to one of their own Contacts."""
    from apps.clients.models import Contact
    from apps.projects.models import Task

    client = get_object_or_404(Client, portal_token=token)
    client_ids = _client_thread_ids(client)
    task = get_object_or_404(
        Task, pk=task_pk, client_visible=True, project__client_fk_id__in=client_ids,
    )

    data = json.loads(request.body)
    contact_pk = data.get('contact_id')

    if contact_pk:
        contact = get_object_or_404(Contact, pk=contact_pk, client_id__in=client_ids)
        task.assigned_to_contact = contact
        task.assigned_to_user = None
    else:
        task.assigned_to_contact = None

    task.save(update_fields=['assigned_to_contact', 'assigned_to_user'])

    return JsonResponse({
        'task_pk': task.pk,
        'assignee_name': task.assigned_to_contact.full_name if task.assigned_to_contact else None,
    })


# -- Per-contact portal ("My Tasks") -- groundwork for individual contact logins --

def contact_portal(request, token):
    """Minimal per-contact portal — lists tasks assigned to this contact.

    Access requires both contact.portal_active and an active parent client,
    so revoking the client's portal access cascades to all of its contacts.
    """
    from apps.projects.models import Task

    contact = get_object_or_404(Contact, portal_token=token)
    client = contact.client

    if not contact.portal_active or client.status != 'active':
        return _apply_portal_headers(render(request, 'portal/contact_inactive.html', {}, status=403))

    cfg = getattr(client, 'portal_config', None)
    accent = (cfg.accent_color if cfg else None) or client.color or '#7c6af7'

    tasks = []
    for t in (Task.objects.filter(assigned_to_contact=contact, client_visible=True)
                  .select_related('project')
                  .order_by('due_date', 'order')):
        tasks.append({
            'pk':            t.pk,
            'title':         t.title,
            'status':        t.status,
            'status_label':  t.get_status_display(),
            'priority':      t.priority,
            'due_date':      t.due_date,
            'project_name':  t.project.name,
            'project_color': t.project.color,
        })

    ctx = {
        'contact':  contact,
        'client':   client,
        'tasks':    tasks,
        'statuses': Task.STATUS,
        'accent':   accent,
    }
    return _apply_portal_headers(render(request, 'portal/contact.html', ctx))


@require_POST
def contact_task_status(request, token, task_pk):
    """Let a contact update the status of a task assigned to them."""
    from django.utils import timezone
    from apps.projects.models import Task

    contact = get_object_or_404(Contact, portal_token=token)
    if not contact.portal_active or contact.client.status != 'active':
        return JsonResponse({'error': 'Portal access disabled'}, status=403)

    task = get_object_or_404(Task, pk=task_pk, assigned_to_contact=contact, client_visible=True)

    data = json.loads(request.body)
    status = data.get('status')
    if status not in dict(Task.STATUS):
        return JsonResponse({'error': 'Invalid status'}, status=400)

    task.status = status
    if status == 'done' and not task.completed_at:
        task.completed_at = timezone.now()
    elif status != 'done':
        task.completed_at = None
    task.save(update_fields=['status', 'completed_at'])

    return JsonResponse({
        'task_pk': task.pk,
        'status': task.status,
        'status_label': task.get_status_display(),
    })

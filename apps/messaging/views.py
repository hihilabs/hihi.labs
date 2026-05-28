import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Thread, Message, Notification, EmailAccount
from .utils import notify
from apps.core.superuser import su_qs, su_get


@login_required
def inbox(request):
    all_threads = (
        Thread.objects.filter(participants=request.user)
        .prefetch_related('messages', 'participants')
        .order_by('-updated_at')
    )
    internal_threads = [t for t in all_threads if t.source == 'internal']
    email_threads = [t for t in all_threads if t.source != 'internal']
    notifications = Notification.objects.filter(user=request.user)[:40]
    unread_notif = Notification.objects.filter(user=request.user, read=False).count()
    unread_internal = sum(t.unread_count(request.user) for t in internal_threads)
    unread_email = sum(t.unread_count(request.user) for t in email_threads)
    email_accounts = EmailAccount.objects.filter(owner=request.user, is_active=True)
    active_tab = request.GET.get('tab', 'internal')
    return render(request, 'messaging/inbox.html', {
        'internal_threads': internal_threads,
        'email_threads': email_threads,
        'notifications': notifications,
        'unread_notif': unread_notif,
        'unread_internal': unread_internal,
        'unread_email': unread_email,
        'email_accounts': email_accounts,
        'active_tab': active_tab,
    })


@login_required
def thread_detail(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    if request.user not in thread.participants.all():
        return redirect('messaging:inbox')
    messages = thread.messages.all()
    # mark all as read
    for msg in messages:
        msg.read_by.add(request.user)
    return render(request, 'messaging/thread.html', {'thread': thread, 'messages': messages})


@login_required
@require_POST
def thread_new(request):
    data = json.loads(request.body)
    subject = data.get('subject', '').strip()
    body = data.get('body', '').strip()
    recipient_ids = data.get('recipients', [])

    if not body:
        return JsonResponse({'error': 'Body required'}, status=400)

    thread = Thread.objects.create(subject=subject, created_by=request.user, source='internal')
    thread.participants.add(request.user)

    recipients = User.objects.filter(pk__in=recipient_ids)
    for r in recipients:
        thread.participants.add(r)

    Message.objects.create(thread=thread, sender=request.user, body=body)

    for r in recipients:
        notify(r, 'message', f'New message: {subject or "No subject"}',
               body=body[:100], link=f'/messaging/thread/{thread.pk}/')

    return JsonResponse({'id': thread.pk})


@login_required
@require_POST
def thread_reply(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    if request.user not in thread.participants.all():
        return JsonResponse({'error': 'Forbidden'}, status=403)

    data = json.loads(request.body)
    body = data.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'Body required'}, status=400)

    msg = Message.objects.create(thread=thread, sender=request.user, body=body)
    thread.save()

    # Process slash commands
    command_result = _process_slash_command(msg, thread, request.user)

    for p in thread.participants.exclude(pk=request.user.pk):
        notify(p, 'message', f'Re: {thread.subject or "message"}',
               body=body[:100], link=f'/messaging/thread/{thread.pk}/')

    return JsonResponse({
        'id': msg.pk,
        'body': msg.body,
        'command': msg.command,
        'command_meta': msg.command_meta,
        'command_result': command_result,
        'sender': request.user.get_short_name() or request.user.username,
        'sent_at': msg.sent_at.strftime('%b %-d, %-I:%M %p'),
    })


@login_required
def message_edit_delete(request, msg_pk):
    msg = get_object_or_404(Message, pk=msg_pk, sender=request.user)
    if request.method == 'DELETE':
        msg.delete()
        return JsonResponse({'ok': True})
    if request.method == 'PATCH':
        data = json.loads(request.body)
        body = data.get('body', '').strip()
        if not body:
            return JsonResponse({'error': 'Body required'}, status=400)
        msg.body = body
        msg.command = ''
        msg.command_meta = {}
        msg.save(update_fields=['body', 'command', 'command_meta'])
        return JsonResponse({'ok': True, 'body': msg.body})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@require_POST
def thread_delete(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    thread.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def notification_delete(request, pk):
    get_object_or_404(Notification, pk=pk).delete()
    return JsonResponse({'ok': True})


def _process_slash_command(msg, thread, user):
    body = msg.body.strip()
    if not body.startswith('/'):
        return None
    parts = body.split(None, 2)
    cmd = parts[0].lower()
    arg = ' '.join(parts[1:]) if len(parts) > 1 else ''

    if cmd == '/task':
        title = arg or 'New task'
        project = thread.project
        result = {'cmd': 'task', 'title': title}
        if project:
            from apps.projects.models import Task
            task = Task.objects.create(
                project=project, title=title,
                created_by=user, status='todo',
            )
            result['task_id'] = task.pk
            result['project'] = project.name
        else:
            result['warn'] = 'No project linked — use /project first'
        msg.command = 'task'
        msg.command_meta = result
        msg.save(update_fields=['command', 'command_meta'])
        return result

    elif cmd == '/project':
        from apps.projects.models import Project
        proj = Project.objects.filter(owner=user, name__icontains=arg).first() if arg else None
        if proj:
            thread.project = proj
            thread.save(update_fields=['project'])
            result = {'cmd': 'project', 'project_id': proj.pk, 'project_name': proj.name}
        else:
            result = {'cmd': 'project', 'warn': f'No project matching "{arg}"'}
        msg.command = 'project'
        msg.command_meta = result
        msg.save(update_fields=['command', 'command_meta'])
        return result

    elif cmd == '/flag':
        thread.flagged = not thread.flagged
        thread.save(update_fields=['flagged'])
        result = {'cmd': 'flag', 'flagged': thread.flagged}
        msg.command = 'flag'
        msg.command_meta = result
        msg.save(update_fields=['command', 'command_meta'])
        return result

    elif cmd == '/note':
        result = {'cmd': 'note', 'title': arg or 'Note', 'body': body[6:].strip()}
        msg.command = 'note'
        msg.command_meta = result
        msg.save(update_fields=['command', 'command_meta'])
        return result

    elif cmd == '/remind':
        result = {'cmd': 'remind', 'when': arg}
        msg.command = 'remind'
        msg.command_meta = result
        msg.save(update_fields=['command', 'command_meta'])
        return result

    return None


@login_required
@require_POST
def email_reply(request, pk):
    """Send an in-app reply to an email thread via Gmail API."""
    thread = get_object_or_404(Thread, pk=pk)
    data = json.loads(request.body)
    body_text = data.get('body', '').strip()
    if not body_text:
        return JsonResponse({'error': 'Body required'}, status=400)

    try:
        credential = request.user.drive_credential
    except Exception:
        return JsonResponse({'error': 'needs_gmail_auth'}, status=401)

    try:
        from apps.files.views import _gmail_service
        import email as email_lib
        import email.mime.text
        import email.mime.multipart
        import base64

        service = _gmail_service(credential)
        last_msg = thread.messages.order_by('-sent_at').first()

        mime = email_lib.mime.multipart.MIMEMultipart()
        mime['To'] = last_msg.from_email if last_msg else ''
        mime['From'] = credential.email
        subject = thread.subject or ''
        mime['Subject'] = f'Re: {subject}' if not subject.lower().startswith('re:') else subject
        if last_msg and last_msg.external_message_id:
            mime['In-Reply-To'] = last_msg.external_message_id
            mime['References'] = last_msg.external_message_id
        mime.attach(email_lib.mime.text.MIMEText(body_text, 'plain'))

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode('utf-8')
        sent = service.users().messages().send(
            userId='me',
            body={'raw': raw, 'threadId': thread.external_thread_id or ''},
        ).execute()

        msg = Message.objects.create(
            thread=thread, sender=request.user,
            body=body_text, from_email=credential.email,
            external_message_id=sent.get('id', ''),
        )
        thread.save()
        return JsonResponse({
            'ok': True,
            'id': msg.pk,
            'sender': credential.email,
            'sent_at': msg.sent_at.strftime('%b %-d, %-I:%M %p'),
        })
    except Exception as e:
        err = str(e)
        if 'insufficientPermissions' in err or 'invalid_grant' in err:
            return JsonResponse({'error': 'needs_gmail_auth'}, status=403)
        return JsonResponse({'error': err}, status=500)


@login_required
def thread_new_from_email(request, pk):
    """Create an internal discussion thread linked to an email thread."""
    email_thread = get_object_or_404(Thread, pk=pk)
    subject = f'[Internal] {email_thread.subject or "email thread"}'
    new_thread = Thread.objects.create(
        subject=subject, created_by=request.user, source='internal',
        project=email_thread.project,
    )
    new_thread.participants.add(request.user)
    Message.objects.create(
        thread=new_thread, sender=request.user,
        body=f'Internal discussion about: {email_thread.subject or "email"}\n/messaging/thread/{pk}/',
    )
    return redirect('messaging:thread_detail', pk=new_thread.pk)


@login_required
@require_POST
def thread_link_project(request, pk):
    """Link or unlink a thread from a project."""
    thread = get_object_or_404(Thread, pk=pk)
    if request.user not in thread.participants.all():
        return JsonResponse({'error': 'Forbidden'}, status=403)
    data = json.loads(request.body)
    project_id = data.get('project_id')
    if project_id:
        from apps.projects.models import Project
        project = su_get(Project, project_id, request.user)
        thread.project = project
        thread.save(update_fields=['project'])
        return JsonResponse({
            'ok': True,
            'project_id': project.pk,
            'project_name': project.name,
            'project_color': project.color,
            'project_url': f'/projects/{project.pk}/',
        })
    else:
        thread.project = None
        thread.save(update_fields=['project'])
        return JsonResponse({'ok': True, 'project_id': None})


@login_required
def projects_search(request):
    """Search user's active projects — used by thread project-link picker."""
    from apps.projects.models import Project
    q = request.GET.get('q', '').strip()
    qs = su_qs(request.user, Project.objects).filter(status='active')
    if q:
        qs = qs.filter(name__icontains=q)
    return JsonResponse({'projects': [
        {'id': p.pk, 'name': p.name, 'color': p.color} for p in qs[:20]
    ]})


# ── Notifications ─────────────────────────────────────────────────────────────

@login_required
def notifications_api(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:40]
    return JsonResponse({'notifications': [
        {
            'id': n.pk, 'type': n.type, 'title': n.title,
            'body': n.body, 'link': n.link, 'read': n.read,
            'created_at': n.created_at.strftime('%b %-d'),
        } for n in notifs
    ]})


@login_required
@require_POST
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(read=True)
    return JsonResponse({'ok': True})


# ── Unread count (for nav badge) ──────────────────────────────────────────────

@login_required
def unread_count(request):
    threads = Thread.objects.filter(participants=request.user)
    msg_unread = sum(t.unread_count(request.user) for t in threads)
    notif_unread = Notification.objects.filter(user=request.user, read=False).count()
    return JsonResponse({'messages': msg_unread, 'notifications': notif_unread})


# ── Email accounts ─────────────────────────────────────────────────────────────

@login_required
def email_accounts(request):
    accounts = EmailAccount.objects.filter(owner=request.user)
    return render(request, 'messaging/email_accounts.html', {'accounts': accounts})


@login_required
@require_POST
def email_account_add(request):
    data = json.loads(request.body)
    acc = EmailAccount.objects.create(
        owner=request.user,
        provider=data.get('provider', 'imap'),
        label=data.get('label', ''),
        email_address=data.get('email_address', ''),
        imap_host=data.get('imap_host', ''),
        imap_port=int(data.get('imap_port', 993)),
        imap_user=data.get('imap_user', ''),
        imap_password=data.get('imap_password', ''),
        use_ssl=data.get('use_ssl', True),
    )
    return JsonResponse({'id': acc.pk, 'label': acc.label})


@login_required
@require_POST
def email_sync(request, account_id):
    """Pull recent messages via IMAP and create Thread/Message records."""
    acc = get_object_or_404(EmailAccount, pk=account_id, owner=request.user, is_active=True)
    try:
        count = _imap_sync(acc, request.user)
        return JsonResponse({'ok': True, 'synced': count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _imap_sync(acc, user, max_messages=50):
    import imaplib
    import email as email_lib
    from email.header import decode_header

    ssl_context = None
    if acc.use_ssl:
        import ssl
        ssl_context = ssl.create_default_context()

    if acc.use_ssl:
        conn = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port, ssl_context=ssl_context)
    else:
        conn = imaplib.IMAP4(acc.imap_host, acc.imap_port)

    conn.login(acc.imap_user, acc.imap_password)
    conn.select('INBOX')

    _, data = conn.search(None, 'ALL')
    msg_ids = data[0].split()[-max_messages:]

    synced = 0
    for mid in reversed(msg_ids):
        _, raw = conn.fetch(mid, '(RFC822)')
        raw_email = raw[0][1]
        msg = email_lib.message_from_bytes(raw_email)

        external_id = msg.get('Message-ID', '').strip()
        if external_id and Message.objects.filter(external_message_id=external_id).exists():
            continue

        subject = _decode_header(msg.get('Subject', ''))
        from_addr = _decode_header(msg.get('From', ''))
        body, html_body = _extract_body(msg)

        thread_id = msg.get('Thread-Index') or msg.get('References') or external_id
        thread = Thread.objects.filter(external_thread_id=thread_id, source=acc.provider).first()
        if not thread:
            thread = Thread.objects.create(
                subject=subject,
                created_by=user,
                source=acc.provider,
                external_thread_id=thread_id or '',
            )
            thread.participants.add(user)

        Message.objects.create(
            thread=thread,
            sender=user,
            body=body,
            html_body=html_body,
            from_email=from_addr,
            external_message_id=external_id,
        )
        synced += 1

    conn.logout()
    acc.last_synced = timezone.now()
    acc.save(update_fields=['last_synced'])
    return synced


def _decode_header(value):
    if not value:
        return ''
    parts = []
    for b, enc in __import__('email.header', fromlist=['decode_header']).decode_header(value):
        if isinstance(b, bytes):
            parts.append(b.decode(enc or 'utf-8', errors='replace'))
        else:
            parts.append(b)
    return ' '.join(parts)


def _extract_body(msg):
    """Return (plain_text, html_body) tuple from email message."""
    plain = ''
    html = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain' and not plain:
                payload = part.get_payload(decode=True)
                if payload:
                    plain = payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
            elif ct == 'text/html' and not html:
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode(msg.get_content_charset() or 'utf-8', errors='replace')
            if msg.get_content_type() == 'text/html':
                html = decoded
            else:
                plain = decoded

    # If no plain text, derive from HTML
    if not plain and html:
        import re
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        plain = '\n'.join(l.strip() for l in text.splitlines() if l.strip())

    return plain, html

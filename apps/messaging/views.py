import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Thread, Message, Notification, EmailAccount
from .utils import notify


@login_required
def inbox(request):
    threads = (
        Thread.objects.filter(participants=request.user)
        .prefetch_related('messages', 'participants')
        .order_by('-updated_at')
    )
    notifications = Notification.objects.filter(user=request.user)[:30]
    unread_notif = Notification.objects.filter(user=request.user, read=False).count()
    email_accounts = EmailAccount.objects.filter(owner=request.user, is_active=True)
    return render(request, 'messaging/inbox.html', {
        'threads': threads,
        'notifications': notifications,
        'unread_notif': unread_notif,
        'email_accounts': email_accounts,
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
    thread.save()  # bumps updated_at

    for p in thread.participants.exclude(pk=request.user.pk):
        notify(p, 'message', f'Re: {thread.subject or "message"}',
               body=body[:100], link=f'/messaging/thread/{thread.pk}/')

    return JsonResponse({
        'id': msg.pk,
        'body': msg.body,
        'sender': request.user.get_short_name() or request.user.username,
        'sent_at': msg.sent_at.strftime('%b %-d, %-I:%M %p'),
    })


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
        body = _extract_body(msg)

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
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                payload = part.get_payload(decode=True)
                return payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or 'utf-8', errors='replace')
    return ''

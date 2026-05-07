from django.db import models
from django.contrib.auth.models import User


class Thread(models.Model):
    SOURCE = [
        ('internal', 'Internal'),
        ('gmail', 'Gmail'),
        ('proton', 'Proton Mail'),
        ('email', 'Email'),
    ]
    subject = models.CharField(max_length=500, blank=True)
    participants = models.ManyToManyField(User, related_name='threads', blank=True)
    project = models.ForeignKey(
        'projects.Project', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='threads',
    )
    source = models.CharField(max_length=20, choices=SOURCE, default='internal')
    external_thread_id = models.CharField(max_length=500, blank=True)  # Gmail thread ID, etc.
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.subject or f'Thread #{self.pk}'

    def last_message(self):
        return self.messages.order_by('-sent_at').first()

    def unread_count(self, user):
        return self.messages.exclude(read_by=user).exclude(sender=user).count()


class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    html_body = models.TextField(blank=True)  # for email import
    from_email = models.CharField(max_length=300, blank=True)  # for inbound email
    external_message_id = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, blank=True, related_name='read_messages')

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f'{self.sender.username} @ {self.sent_at:%Y-%m-%d %H:%M}'


class Notification(models.Model):
    TYPES = [
        ('invoice_paid', 'Invoice Paid'),
        ('invoice_sent', 'Invoice Sent'),
        ('invoice_overdue', 'Invoice Overdue'),
        ('timer_stopped', 'Timer Stopped'),
        ('task_done', 'Task Completed'),
        ('message', 'New Message'),
        ('subscription_renewed', 'Subscription Renewed'),
        ('subscription_expired', 'Subscription Expired'),
        ('subscription_pending', 'Payment Pending'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPES)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=300, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.title}'


# ── Email account config (phase 2 IMAP) ──────────────────────────────────────

class EmailAccount(models.Model):
    PROVIDER = [('gmail', 'Gmail'), ('proton', 'Proton (Bridge)'), ('imap', 'Generic IMAP')]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER)
    label = models.CharField(max_length=50)         # "Work Gmail", "Proton"
    email_address = models.EmailField()
    imap_host = models.CharField(max_length=200)
    imap_port = models.IntegerField(default=993)
    imap_user = models.CharField(max_length=200)
    imap_password = models.CharField(max_length=500)  # store encrypted in production
    use_ssl = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['label']

    def __str__(self):
        return f'{self.label} ({self.email_address})'

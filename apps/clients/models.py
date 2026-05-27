from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    STATUS = [
        ('lead',     'Lead'),
        ('active',   'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]
    owner         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients')
    name          = models.CharField(max_length=200)
    company       = models.CharField(max_length=200, blank=True)
    email         = models.EmailField(blank=True)
    phone         = models.CharField(max_length=50, blank=True)
    website       = models.URLField(max_length=500, blank=True)
    address       = models.TextField(blank=True)
    city          = models.CharField(max_length=100, blank=True)
    state         = models.CharField(max_length=100, blank=True)
    country       = models.CharField(max_length=100, blank=True)
    notes         = models.TextField(blank=True)
    color         = models.CharField(max_length=7, default='#7c6af7')
    status        = models.CharField(max_length=20, choices=STATUS, default='active')
    hosted_domain = models.CharField(max_length=200, blank=True,
                        help_text='Domain hosted on this server — enables in-CRM email management.')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.company or self.name

    @property
    def pipeline_stage(self):
        return self.get_status_display()


class Contact(models.Model):
    client     = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacts')
    owner      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100, blank=True)
    email      = models.EmailField(blank=True)
    phone      = models.CharField(max_length=50, blank=True)
    role       = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'first_name']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class FollowUp(models.Model):
    PRIORITY = [('low', 'Low'), ('normal', 'Normal'), ('high', 'High')]
    client     = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='followups')
    owner      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followups')
    note       = models.TextField()
    due_date   = models.DateField(null=True, blank=True)
    priority   = models.CharField(max_length=10, choices=PRIORITY, default='normal')
    done       = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    done_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['done', 'due_date', '-created_at']

    def __str__(self):
        return f'Follow-up: {self.client.display_name} — {self.note[:60]}'


class HostingSubscription(models.Model):
    CYCLE = [('monthly', 'Monthly'), ('annual', 'Annual'), ('one-time', 'One-time')]
    owner              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosting_subscriptions')
    client             = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='hosting_subscriptions')
    domain             = models.CharField(max_length=200, help_text='Primary domain being hosted')
    additional_domains = models.TextField(blank=True, help_text='Comma-separated additional domains')
    plan_name          = models.CharField(max_length=100, default='VPS Hosting')
    price              = models.DecimalField(max_digits=8, decimal_places=2)
    billing_cycle      = models.CharField(max_length=20, choices=CYCLE, default='monthly')
    previous_provider  = models.CharField(max_length=100, blank=True)
    server_path        = models.CharField(max_length=300, blank=True, help_text='e.g. /var/www/vhosts/.../project/')
    notes              = models.TextField(blank=True)
    started            = models.DateField(null=True, blank=True)
    next_invoice_date  = models.DateField(null=True, blank=True)
    is_active          = models.BooleanField(default=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['domain']

    def __str__(self):
        return f'{self.domain} ({self.client.display_name})'

    @property
    def price_display(self):
        return f'${self.price}/{self.billing_cycle}'

    @property
    def additional_domain_list(self):
        return [d.strip() for d in self.additional_domains.split(',') if d.strip()]

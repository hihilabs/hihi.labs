from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Proposal(models.Model):
    STATUS = [
        ('draft',    'Draft'),
        ('sent',     'Sent'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('void',     'Void'),
    ]
    owner      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposals')
    client     = models.ForeignKey('clients.Client', on_delete=models.SET_NULL,
                     null=True, blank=True, related_name='proposals')
    project    = models.ForeignKey('projects.Project', on_delete=models.SET_NULL,
                     null=True, blank=True, related_name='proposals')
    number     = models.CharField(max_length=30)
    title      = models.CharField(max_length=300)
    status     = models.CharField(max_length=20, choices=STATUS, default='draft')
    intro      = models.TextField(blank=True)
    notes      = models.TextField(blank=True)
    tax_rate   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    valid_until = models.DateField(null=True, blank=True)
    sent_at    = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.number} — {self.title}'

    @staticmethod
    def next_number(owner):
        last = Proposal.objects.filter(owner=owner).order_by('-created_at').first()
        if not last:
            return 'PROP-001'
        try:
            n = int(last.number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            n = 1
        return f'PROP-{n:03d}'

    @property
    def subtotal(self):
        return sum(line.amount for line in self.lines.all())

    @property
    def tax_amount(self):
        return self.subtotal * (self.tax_rate / 100)

    @property
    def total(self):
        return self.subtotal + self.tax_amount


class ProposalLine(models.Model):
    proposal    = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=300)
    quantity    = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    rate        = models.DecimalField(max_digits=8, decimal_places=2)
    order       = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'pk']

    @property
    def amount(self):
        return self.quantity * self.rate

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
import datetime


class Invoice(models.Model):
    STATUS = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('void', 'Void'),
    ]
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    client_fk = models.ForeignKey(
        'clients.Client', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoices',
    )
    number = models.CharField(max_length=30)          # e.g. INV-031
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    issued_date = models.DateField(default=date.today)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.number} — {self.client_name}'

    @property
    def subtotal(self):
        return sum(line.amount for line in self.lines.all())

    @property
    def total(self):
        return self.subtotal

    def next_number(owner):
        last = Invoice.objects.filter(owner=owner).order_by('-created_at').first()
        if not last:
            return 'INV-031'
        try:
            n = int(last.number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            n = 31
        return f'INV-{n:03d}'


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)   # hours
    rate = models.DecimalField(max_digits=8, decimal_places=2)        # $/hr
    project = models.ForeignKey(
        'projects.Project', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoice_lines',
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'pk']

    def __str__(self):
        return self.description

    @property
    def amount(self):
        return self.quantity * self.rate


class CostSettings(models.Model):
    """Singleton: global cost basis used by the value board's cost/sustain/pricing modes."""
    labor_cost_per_hour = models.DecimalField(
        max_digits=8, decimal_places=2, default=40,
        help_text='What an hour of work actually costs you (not the client bill rate).')
    ai_cost_per_1k_tokens = models.DecimalField(
        max_digits=8, decimal_places=4, default=0.01,
        help_text='Blended $ per 1k tokens across the AI stack.')
    overhead_monthly = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Fixed monthly overhead: hosting, electricity, software subs, accounting…')
    target_margin_pct = models.DecimalField(
        max_digits=6, decimal_places=2, default=150,
        help_text='Markup over cost floor, in percent (150 = price at 2.5x cost).')
    default_client_factor = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0,
        help_text='Pricing multiplier used when a client has no pricing_factor set.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cost settings'
        verbose_name_plural = 'Cost settings'

    def __str__(self):
        return 'Cost settings'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ProjectExpense(models.Model):
    KIND = [('one_time', 'One-time'), ('monthly', 'Monthly recurring')]
    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, related_name='expenses')
    kind = models.CharField(max_length=10, choices=KIND, default='one_time')
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=date.today)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.project.name}: {self.description} (${self.amount})'

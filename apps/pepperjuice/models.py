import math
from datetime import date

from django.contrib.auth.models import User
from django.db import models


class SequenceConnection(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sequence_connection')
    api_key = models.CharField(max_length=500)
    display_name = models.CharField(max_length=100, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} — Sequence'


class CachedAccount(models.Model):
    TYPE_CHOICES = [('pod', 'Pod'), ('income', 'Income Source'), ('external', 'External')]
    SUBTYPE_CHOICES = [
        ('cash',       'Cash / Checking / Savings'),
        ('investment', 'Investment / Retirement'),
        ('loan',       'Loan'),
        ('credit',     'Credit Card'),
        ('crypto',     'Crypto'),
        ('bucket',     'Budget Bucket'),
        ('other',      'Other'),
    ]

    connection = models.ForeignKey(SequenceConnection, on_delete=models.CASCADE, related_name='accounts')
    sequence_id = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    institution = models.CharField(max_length=200, blank=True)
    account_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='pod')
    account_subtype = models.CharField(max_length=20, choices=SUBTYPE_CHOICES, default='other')
    balance_cents = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default='USD')
    is_business = models.BooleanField(default=False)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [('connection', 'sequence_id')]

    def __str__(self):
        return f'{self.name} — {self.balance_display}'

    @property
    def balance_display(self):
        return f'${self.balance_cents / 100:,.2f}'


class Bill(models.Model):
    CATEGORIES = [
        ('housing',       'Housing'),
        ('utilities',     'Utilities'),
        ('subscriptions', 'Subscriptions'),
        ('insurance',     'Insurance'),
        ('debt',          'Debt'),
        ('family',        'Family'),
        ('business',      'Business'),
        ('other',         'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pepperjuice_bills')
    name = models.CharField(max_length=200)
    amount_cents = models.IntegerField()
    due_day = models.IntegerField(help_text='Day of month (1–31)')
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other')
    is_auto_pay = models.BooleanField(default=False)
    is_business = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sequence_rule_id = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['due_day', 'name']

    def __str__(self):
        return f'{self.name} — ${self.amount_cents / 100:.2f} (day {self.due_day})'

    @property
    def amount_display(self):
        return f'${self.amount_cents / 100:,.2f}'

    def paid_this_month(self):
        today = date.today()
        return self.payments.filter(
            paid_date__year=today.year,
            paid_date__month=today.month,
        ).exists()

    def is_overdue(self):
        today = date.today()
        return not self.paid_this_month() and today.day > self.due_day


class BillPayment(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    paid_date = models.DateField(default=date.today)
    amount_cents = models.IntegerField()
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_date']

    def __str__(self):
        return f'{self.bill.name} paid {self.paid_date}'


class SavingsGoal(models.Model):
    GOAL_TYPES = [
        ('college',     'College Fund'),
        ('parent_loan', 'Parent Loan Payoff'),
        ('emergency',   'Emergency Fund'),
        ('investment',  'Investment'),
        ('vacation',    'Vacation'),
        ('other',       'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(max_length=200)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES, default='other')
    target_cents = models.BigIntegerField()
    current_cents = models.BigIntegerField(default=0)
    monthly_contribution_cents = models.IntegerField(default=0)
    target_date = models.DateField(null=True, blank=True)
    sequence_account_id = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def progress_pct(self):
        if not self.target_cents:
            return 0
        return min(100, round(self.current_cents / self.target_cents * 100, 1))

    @property
    def remaining_cents(self):
        return max(0, self.target_cents - self.current_cents)

    @property
    def months_to_goal(self):
        if not self.monthly_contribution_cents or self.remaining_cents == 0:
            return 0
        return math.ceil(self.remaining_cents / self.monthly_contribution_cents)

from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Expense(models.Model):
    CATEGORIES = [
        ('software',      'Software & Subscriptions'),
        ('equipment',     'Equipment & Hardware'),
        ('home_office',   'Home Office'),
        ('travel',        'Travel & Transportation'),
        ('meals',         'Meals & Entertainment'),
        ('professional',  'Professional Services'),
        ('marketing',     'Marketing & Advertising'),
        ('education',     'Education & Training'),
        ('other',         'Other'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    date = models.DateField(default=date.today)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vendor = models.CharField(max_length=200)
    description = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other')
    is_deductible = models.BooleanField(default=True)
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.vendor} ${self.amount} ({self.date})'

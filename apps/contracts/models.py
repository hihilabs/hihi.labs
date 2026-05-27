from django.db import models
from django.contrib.auth.models import User


class Contract(models.Model):
    STATUS = [
        ('draft',   'Draft'),
        ('sent',    'Sent'),
        ('signed',  'Signed'),
        ('expired', 'Expired'),
        ('void',    'Void'),
    ]
    owner      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contracts')
    client     = models.ForeignKey('clients.Client', on_delete=models.SET_NULL,
                     null=True, blank=True, related_name='contracts')
    project    = models.ForeignKey('projects.Project', on_delete=models.SET_NULL,
                     null=True, blank=True, related_name='contracts')
    number     = models.CharField(max_length=30)
    title      = models.CharField(max_length=300)
    status     = models.CharField(max_length=20, choices=STATUS, default='draft')
    body       = models.TextField(blank=True)
    value      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date   = models.DateField(null=True, blank=True)
    signed_at  = models.DateTimeField(null=True, blank=True)
    signed_by  = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.number} — {self.title}'

    @staticmethod
    def next_number(owner):
        last = Contract.objects.filter(owner=owner).order_by('-created_at').first()
        if not last:
            return 'CTR-001'
        try:
            n = int(last.number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            n = 1
        return f'CTR-{n:03d}'

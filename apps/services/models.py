from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Service(models.Model):
    RECURRENCE = [
        ('one-time', 'One-time'), ('weekly', 'Weekly'),
        ('monthly', 'Monthly'), ('annual', 'Annual'),
    ]
    name         = models.CharField(max_length=200)
    slug         = models.SlugField(max_length=200, unique=True)
    description  = models.TextField(blank=True)
    icon         = models.CharField(max_length=60, default='fa-wrench',
                       help_text='FontAwesome icon class')
    color        = models.CharField(max_length=7, default='#7c6af7')
    recurrence   = models.CharField(max_length=20, choices=RECURRENCE, default='monthly')
    day_of_month = models.IntegerField(default=1,
                       help_text='For monthly: day to trigger (1-28)')
    owner        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def active_project_count(self):
        return self.project_services.filter(enabled=True).count()


class ProjectService(models.Model):
    project      = models.ForeignKey('projects.Project', on_delete=models.CASCADE,
                       related_name='project_services')
    service      = models.ForeignKey(Service, on_delete=models.CASCADE,
                       related_name='project_services')
    enabled      = models.BooleanField(default=True)
    last_checked = models.DateField(null=True, blank=True)
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('project', 'service')]

    def __str__(self):
        return f'{self.service.name} → {self.project.name}'

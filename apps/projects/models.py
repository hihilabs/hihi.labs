from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Project(models.Model):
    STATUS = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('done', 'Done'),
        ('archived', 'Archived'),
    ]
    name = models.CharField(max_length=200)
    client = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='active')
    color = models.CharField(max_length=7, default='#7c6af7')
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=150)
    hihi_crm_project_id = models.IntegerField(null=True, blank=True, help_text='rise_projects.id for sync')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.client})' if self.client else self.name

    def total_hours(self):
        secs = sum(e.duration_seconds() for e in self.time_entries.filter(ended_at__isnull=False))
        return round(secs / 3600, 2)

    def unbilled_hours(self):
        secs = sum(e.duration_seconds() for e in self.time_entries.filter(ended_at__isnull=False, billed=False))
        return round(secs / 3600, 2)


class Task(models.Model):
    PRIORITY = [('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')]
    STATUS = [('todo', 'To Do'), ('doing', 'Doing'), ('blocked', 'Blocked'), ('done', 'Done')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=300)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='todo')
    priority = models.CharField(max_length=10, choices=PRIORITY, default='normal')
    claude_suggestion = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title

    def total_hours(self):
        secs = sum(e.duration_seconds() for e in self.time_entries.filter(ended_at__isnull=False))
        return round(secs / 3600, 2)


class TimeEntry(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='time_entries')
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='time_entries')
    description = models.CharField(max_length=300, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    billed = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_entries')

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.project.name} — {self.started_at:%Y-%m-%d %H:%M}'

    def duration_seconds(self):
        if not self.ended_at:
            return 0
        return int((self.ended_at - self.started_at).total_seconds())

    def duration_display(self):
        secs = self.duration_seconds()
        h, rem = divmod(secs, 3600)
        m = rem // 60
        return f'{h}h {m:02d}m' if h else f'{m}m'

    def is_running(self):
        return self.ended_at is None

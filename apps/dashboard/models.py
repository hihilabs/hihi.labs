from django.db import models
from django.contrib.auth.models import User


class UserCalendarFeed(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_feeds')
    name      = models.CharField(max_length=100)
    ics_url   = models.URLField(max_length=1000)
    color     = models.CharField(max_length=7, default='#7c6af7')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'name')

    def __str__(self):
        return f'{self.user.username} — {self.name}'


class ProjectSubscription(models.Model):
    """A user "grabs" a project so its tasks appear in their dashboard task list."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grabbed_projects')
    project    = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='subscribers')
    grabbed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'project')
        ordering = ['-grabbed_at']

    def __str__(self):
        return f'{self.user.username} → {self.project.name}'


class QuickNote(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quick_notes')
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.content[:60]}'

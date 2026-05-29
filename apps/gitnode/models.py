from django.db import models
from apps.servers.models import Server


class ManagedRepo(models.Model):
    server   = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='repos')
    name     = models.CharField(max_length=100)
    path     = models.CharField(max_length=500, help_text='Absolute path on the server, e.g. /var/www/vhosts/danklean.com/django')
    branch   = models.CharField(max_length=100, default='master')
    color    = models.CharField(max_length=7, default='#7c6af7')
    icon     = models.CharField(max_length=40, default='fa-code-branch')
    github_url = models.URLField(blank=True)
    service_name = models.CharField(max_length=100, blank=True, help_text='systemd service to restart after deploy, e.g. danklean')
    order    = models.PositiveIntegerField(default=0)
    active   = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.name} ({self.server.name})'

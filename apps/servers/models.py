from django.db import models
from django.contrib.auth.models import User


class Server(models.Model):
    ICONS = [
        ('fa-server', 'Server'),
        ('fa-cloud', 'Cloud'),
        ('fa-database', 'Database'),
        ('fa-docker', 'Docker'),
        ('fa-linux', 'Linux'),
        ('fa-raspberry-pi', 'Pi'),
        ('fa-network-wired', 'Network'),
        ('fa-shield', 'VPN / Secure'),
    ]

    PLATFORMS = [
        ('vps',      'VPS'),
        ('docker',   'Docker / VPS'),
        ('unraid',   'Unraid'),
        ('external', 'External'),
        ('local',    'Local'),
    ]

    SERVICE_TYPES = [
        ('django', 'Django'),
        ('node',   'Node.js'),
        ('nginx',  'Static / nginx'),
        ('docker', 'Docker app'),
        ('ssh',    'SSH server'),
        ('other',  'Other'),
    ]

    owner        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='servers')
    name         = models.CharField(max_length=100)
    host         = models.CharField(max_length=255)
    ssh_user     = models.CharField(max_length=100, default='root')
    port         = models.IntegerField(default=22)
    tags         = models.CharField(max_length=200, blank=True)
    notes        = models.TextField(blank=True)
    icon         = models.CharField(max_length=40, choices=ICONS, default='fa-server')
    color        = models.CharField(max_length=7, default='#7c6af7')
    # Fleet fields
    domain       = models.URLField(blank=True, help_text='Public URL, e.g. https://hihilabs.xyz')
    git_repo     = models.URLField(blank=True, help_text='GitHub repo URL')
    platform     = models.CharField(max_length=20, choices=PLATFORMS, default='vps')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES, default='ssh')
    status_url   = models.URLField(blank=True, help_text='Health-check URL (HTTP 2xx = up)')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['platform', 'name']

    def __str__(self):
        return f'{self.name} ({self.host})'

    def ssh_url(self):
        if self.port == 22:
            return f'ssh://{self.ssh_user}@{self.host}'
        return f'ssh://{self.ssh_user}@{self.host}:{self.port}'

    def ssh_command(self):
        if self.port == 22:
            return f'ssh {self.ssh_user}@{self.host}'
        return f'ssh -p {self.port} {self.ssh_user}@{self.host}'

    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def platform_label(self):
        return dict(self.PLATFORMS).get(self.platform, self.platform)

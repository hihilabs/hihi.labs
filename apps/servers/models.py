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

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='servers')
    name = models.CharField(max_length=100)
    host = models.CharField(max_length=255)
    ssh_user = models.CharField(max_length=100, default='root')
    port = models.IntegerField(default=22)
    tags = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    icon = models.CharField(max_length=40, choices=ICONS, default='fa-server')
    color = models.CharField(max_length=7, default='#7c6af7')
    monthly_cost = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text='What this server costs per month (hosting bill, amortized hardware + power).')
    projects = models.ManyToManyField(
        'projects.Project', blank=True, related_name='servers',
        help_text='Projects this server supports — its monthly cost is split evenly across them.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

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

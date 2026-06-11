import secrets
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
    domain       = models.URLField(blank=True)
    git_repo     = models.URLField(blank=True)
    platform     = models.CharField(max_length=20, choices=PLATFORMS, default='vps')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES, default='ssh')
    status_url   = models.URLField(blank=True)
    monthly_cost = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text='What this server costs per month (hosting bill, amortized hardware + power).')
    projects     = models.ManyToManyField(
        'projects.Project', blank=True, related_name='servers',
        help_text='Projects this server supports — its monthly cost is split evenly across them.')
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


# ── Developer identity registry ───────────────────────────────────────────────

class Developer(models.Model):
    """Known developers who work on VPS projects."""
    user        = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='developer_profile')
    display_name = models.CharField(max_length=100)
    email        = models.EmailField(blank=True)
    work_email   = models.EmailField(blank=True, help_text='e.g. quinn@hihilabs.xyz')
    github_login = models.CharField(max_length=100, blank=True)
    linux_user   = models.CharField(max_length=64, blank=True, help_text='Linux username on VPS')
    color        = models.CharField(max_length=7, default='#7c6af7')
    avatar_emoji = models.CharField(max_length=8, default='👤')
    ssh_key_fingerprints = models.TextField(blank=True,
        help_text='One SHA256 fingerprint per line — used to identify device on login')
    notes        = models.TextField(blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

    def fingerprint_list(self):
        return [f.strip() for f in self.ssh_key_fingerprints.splitlines() if f.strip()]


# ── Work sessions ─────────────────────────────────────────────────────────────

class WorkSession(models.Model):
    """Tracks who is actively working on what project/server."""
    STATUS = [
        ('active',   'Active'),
        ('idle',     'Idle'),
        ('checked_out', 'Checked out'),
    ]

    developer    = models.ForeignKey(Developer, on_delete=models.CASCADE, related_name='sessions')
    server       = models.ForeignKey(Server, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='sessions')
    project_name = models.CharField(max_length=200, blank=True)
    task_summary = models.TextField(blank=True, help_text='What are you working on?')
    status       = models.CharField(max_length=20, choices=STATUS, default='active')
    # Device fingerprinting
    ssh_fingerprint = models.CharField(max_length=200, blank=True)
    client_ip       = models.GenericIPAddressField(null=True, blank=True)
    client_hostname = models.CharField(max_length=200, blank=True)
    # Token for the terminal hook to post updates without full auth
    session_token   = models.CharField(max_length=64, default=secrets.token_hex)
    checked_in_at   = models.DateTimeField(auto_now_add=True)
    last_seen_at    = models.DateTimeField(auto_now=True)
    checked_out_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-checked_in_at']

    def __str__(self):
        return f'{self.developer} on {self.project_name or self.server} ({self.status})'

    def duration_display(self):
        from django.utils import timezone
        end = self.checked_out_at or timezone.now()
        delta = end - self.checked_in_at
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        return f'{h}h {m}m' if h else f'{m}m'

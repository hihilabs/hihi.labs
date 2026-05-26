import secrets
from django.db import models
from django.utils import timezone


class Client(models.Model):
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(unique=True)
    api_key     = models.CharField(max_length=64, unique=True, default=secrets.token_hex)
    color       = models.CharField(max_length=7, default='#7c6af7')
    gpu_priority   = models.IntegerField(default=50, help_text='0–100; higher = more GPU time')
    api_priority   = models.IntegerField(default=50, help_text='0–100; higher = more Claude API quota')
    active      = models.BooleanField(default=True)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-gpu_priority', 'name']

    def __str__(self):
        return self.name


class WorkerNode(models.Model):
    TYPES = [
        ('pull',    'Pull Worker'),
        ('ocr',     'OCR Server'),
        ('labeler', 'Labeler'),
        ('hybrid',  'Hybrid'),
    ]
    name         = models.CharField(max_length=100, unique=True)
    worker_type  = models.CharField(max_length=20, choices=TYPES, default='pull')
    ip           = models.GenericIPAddressField(null=True, blank=True)
    gpu          = models.CharField(max_length=100, blank=True)
    capabilities = models.JSONField(default=list)   # ['gpu_ocr', 'claude_vision', 'cpu']
    last_seen    = models.DateTimeField(null=True, blank=True)
    cpu_pct      = models.FloatField(null=True, blank=True)
    mem_pct      = models.FloatField(null=True, blank=True)
    vram_used    = models.IntegerField(null=True, blank=True)
    vram_total   = models.IntegerField(null=True, blank=True)
    active_jobs  = models.IntegerField(default=0)
    current_job  = models.JSONField(null=True, blank=True)
    version      = models.CharField(max_length=40, blank=True)
    secret_key   = models.CharField(max_length=64, default=secrets.token_hex)
    pending_command = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def online(self):
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).total_seconds() < 90


class JobType(models.Model):
    slug           = models.CharField(max_length=50, unique=True)
    label          = models.CharField(max_length=100)
    requires_gpu   = models.BooleanField(default=False)
    requires_claude= models.BooleanField(default=False)
    description    = models.TextField(blank=True)

    class Meta:
        ordering = ['label']

    def __str__(self):
        return self.label


class Job(models.Model):
    STATUS   = [('queued','Queued'),('claimed','Claimed'),('running','Running'),
                ('done','Done'),('error','Error')]
    PRIORITY = [(1,'Low'),(5,'Normal'),(10,'High'),(20,'Urgent')]

    client       = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='jobs')
    job_type     = models.ForeignKey(JobType, on_delete=models.SET_NULL, null=True, blank=True)
    worker       = models.ForeignKey(WorkerNode, null=True, blank=True, on_delete=models.SET_NULL)
    priority     = models.IntegerField(default=5, choices=PRIORITY)
    status       = models.CharField(max_length=20, choices=STATUS, default='queued')
    label        = models.CharField(max_length=200, blank=True)  # human-readable description
    payload      = models.JSONField(default=dict)
    result       = models.JSONField(null=True, blank=True)
    error        = models.TextField(blank=True)
    progress     = models.JSONField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    claimed_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-priority', 'created_at']

    def __str__(self):
        return f'Job #{self.pk} [{self.status}] — {self.client}'

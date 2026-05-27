from django.db import models
from django.contrib.auth.models import User


# ── Existing models (tables already in DB) ────────────────────────────────────

class GoogleToken(models.Model):
    """Legacy Google OAuth token storage."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='google_token')
    token_json = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} google token'


class ClientFile(models.Model):
    SOURCES = [('upload', 'Upload'), ('drive', 'Google Drive')]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_files')
    client = models.ForeignKey(
        'clients.Client', on_delete=models.CASCADE, null=True, blank=True,
        related_name='files',
    )
    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, null=True, blank=True,
        related_name='files',
    )
    name = models.CharField(max_length=300)
    description = models.CharField(max_length=500, blank=True)
    file = models.FileField(upload_to='client_files/', blank=True, null=True)
    drive_file_id = models.CharField(max_length=200, blank=True)
    drive_web_view_link = models.CharField(max_length=200, blank=True)
    drive_web_content_link = models.CharField(max_length=200, blank=True)
    drive_thumbnail_link = models.CharField(max_length=200, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.BigIntegerField(default=0)
    source = models.CharField(max_length=10, choices=SOURCES, default='upload')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def ext(self):
        return self.name.rsplit('.', 1)[-1].lower() if '.' in self.name else ''

    @property
    def is_image(self):
        return self.mime_type.startswith('image/') or self.ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'svg')


# ── New models ────────────────────────────────────────────────────────────────

class DriveCredential(models.Model):
    """Enhanced Google Drive OAuth credential (replaces GoogleToken for new auth flow)."""
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='drive_credential')
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.owner.username} — {self.email}'


class DriveFolder(models.Model):
    """A Google Drive folder linked to a project or client."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drive_folders')
    drive_folder_id = models.CharField(max_length=200)
    name = models.CharField(max_length=300)
    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, null=True, blank=True,
        related_name='drive_folders',
    )
    client = models.ForeignKey(
        'clients.Client', on_delete=models.CASCADE, null=True, blank=True,
        related_name='drive_folders',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

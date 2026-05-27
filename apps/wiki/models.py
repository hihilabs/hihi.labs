from django.db import models
from django.contrib.auth.models import User


class WikiSection(models.Model):
    slug       = models.SlugField(max_length=100, unique=True)
    title      = models.CharField(max_length=200)
    content_md = models.TextField(blank=True)
    diagram_mermaid = models.TextField(blank=True)
    order      = models.IntegerField(default=0)
    parent     = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children',
    )
    collapsed  = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='wiki_sections',
    )

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


class WikiNote(models.Model):
    section    = models.ForeignKey(WikiSection, on_delete=models.CASCADE, related_name='notes')
    body       = models.TextField()
    pinned     = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned', '-created_at']

    def __str__(self):
        return f'Note on {self.section.title}: {self.body[:40]}'

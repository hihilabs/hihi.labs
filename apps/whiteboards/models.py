from django.db import models
from django.contrib.auth.models import User


class Whiteboard(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='whiteboards')
    title = models.CharField(max_length=200)
    data = models.TextField(default='{}')
    project = models.ForeignKey(
        'projects.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='whiteboards',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

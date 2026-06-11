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


class RoomEvent(models.Model):
    """One line in a room's running transcript — speech, chat, board actions,
    commands, loyd replies, system notices. The transcript pane renders these
    live; old rooms replay from here."""
    KIND_CHOICES = [
        ('chat', 'Chat'),
        ('speech', 'Speech'),
        ('board', 'Board action'),
        ('command', 'Slash command'),
        ('loyd', 'Loyd'),
        ('system', 'System'),
        ('sandbox', 'Sandbox'),
    ]
    board = models.ForeignKey(Whiteboard, on_delete=models.CASCADE, related_name='events')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='room_events')
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default='chat')
    text = models.TextField()
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.kind}] {self.text[:40]}'


class Sandbox(models.Model):
    """A throwaway dev container spun up from a room — module picker picks the
    template, files live under sandboxes/<pk>/ and are editable in-room."""
    STATUS = [('running', 'Running'), ('stopped', 'Stopped'), ('error', 'Error')]

    board = models.ForeignKey(Whiteboard, on_delete=models.CASCADE, related_name='sandboxes')
    template = models.CharField(max_length=30)
    container = models.CharField(max_length=80, blank=True)
    port = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS, default='running')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='sandboxes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'sandbox {self.pk} [{self.template}] {self.status}'

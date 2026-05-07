from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f'Chat #{self.pk}'

    def auto_title(self):
        first = self.messages.filter(role='user').first()
        if first:
            self.title = first.content[:80]
            self.save(update_fields=['title'])


class Message(models.Model):
    ROLES = [('user', 'User'), ('assistant', 'Assistant')]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tokens_used = models.IntegerField(default=0)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role}: {self.content[:60]}'


class TemplateCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=60, default='fa-solid fa-wand-magic-sparkles')
    order = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Template categories'

    def __str__(self):
        return self.name


class PromptTemplate(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.ForeignKey(TemplateCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='templates')
    icon = models.CharField(max_length=60, default='fa-solid fa-file-lines')
    system_prompt = models.TextField(blank=True, help_text='System context for Claude. Leave blank for default.')
    prompt_template = models.TextField(help_text='Use {{variable_name}} placeholders.')
    variables = models.JSONField(default=list, help_text='[{"name": "client", "label": "Client Name", "type": "text"}]')
    use_smart_model = models.BooleanField(default=False, help_text='Use Sonnet instead of Haiku.')
    active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class GeneratedDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    template = models.ForeignKey(PromptTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    inputs_used = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class VoiceNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='voice_notes')
    audio_file = models.FileField(upload_to='voice_notes/', blank=True)
    transcript = models.TextField(blank=True)
    duration_s = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optionally link to a project task note
    linked_to = models.CharField(max_length=200, blank=True, help_text='e.g. projects:42')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Voice note {self.pk} — {self.transcript[:60]}'

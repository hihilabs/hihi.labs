from django.db import models


class ClientPortalConfig(models.Model):
    THEMES = [
        ('default',  'Default'),
        ('infinity', 'Infinity'),
        ('minimal',  'Minimal'),
    ]

    client          = models.OneToOneField('clients.Client', on_delete=models.CASCADE, related_name='portal_config')
    portal_theme    = models.CharField(max_length=20, choices=THEMES, default='default')
    show_projects   = models.BooleanField(default=True)
    show_invoices   = models.BooleanField(default=True)
    show_files      = models.BooleanField(default=True)
    show_tickets    = models.BooleanField(default=True)
    show_messages   = models.BooleanField(default=False)
    welcome_message = models.TextField(blank=True)
    accent_color    = models.CharField(max_length=7, default='#7c6af7')
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.client} portal config'


class SiteFooter(models.Model):
    TYPES = [('public', 'Public Site'), ('portal', 'Client Portal')]

    footer_type       = models.CharField(max_length=10, choices=TYPES, unique=True)
    html_content      = models.TextField(blank=True, help_text='HTML injected into the footer.')
    show_ticket_form  = models.BooleanField(default=False)
    ticket_form_title = models.CharField(max_length=200, default='Submit a Ticket')
    updated_at        = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.get_footer_type_display()} Footer'

    @classmethod
    def get(cls, footer_type):
        obj, _ = cls.objects.get_or_create(footer_type=footer_type)
        return obj

from django.contrib import admin
from .models import Ticket, TicketComment

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'type', 'priority', 'reporter', 'created_at']
    list_filter  = ['status', 'type', 'priority']
    search_fields = ['title', 'body']

admin.site.register(TicketComment)

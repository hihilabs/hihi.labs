from django.contrib import admin
from .models import Thread, Message, Notification, EmailAccount


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'sent_at', 'body')
    can_delete = False


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('subject', 'source', 'created_by', 'updated_at')
    list_filter = ('source',)
    inlines = [MessageInline]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'read', 'created_at')
    list_filter = ('type', 'read')
    search_fields = ('user__username', 'title')


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ('owner', 'label', 'provider', 'email_address', 'last_synced', 'is_active')
    list_editable = ('is_active',)

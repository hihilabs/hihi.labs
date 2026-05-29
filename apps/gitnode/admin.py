from django.contrib import admin
from .models import ManagedRepo

@admin.register(ManagedRepo)
class ManagedRepoAdmin(admin.ModelAdmin):
    list_display  = ['name', 'server', 'path', 'branch', 'service_name', 'active', 'order']
    list_editable = ['order', 'active']
    list_filter   = ['server', 'active']

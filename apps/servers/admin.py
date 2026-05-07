from django.contrib import admin
from .models import Server


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'ssh_user', 'port', 'owner', 'created_at')
    search_fields = ('name', 'host', 'tags')

from django.contrib import admin
from .models import GameServer


@admin.register(GameServer)
class GameServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip', 'port', 'active')
    list_editable = ('active',)

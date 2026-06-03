from django.contrib import admin
from .models import UserCalendarFeed, ProjectSubscription, QuickNote


@admin.register(UserCalendarFeed)
class UserCalendarFeedAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'color', 'is_active', 'created_at')
    list_filter  = ('is_active', 'user')


@admin.register(ProjectSubscription)
class ProjectSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'grabbed_at')
    list_filter  = ('user',)


@admin.register(QuickNote)
class QuickNoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'created_at')
    list_filter  = ('user',)

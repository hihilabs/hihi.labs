from django.contrib import admin
from .models import Project, Task, TimeEntry


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'status', 'total_hours', 'unbilled_hours', 'hourly_rate']
    list_filter = ['status', 'owner']
    search_fields = ['name', 'client']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'priority', 'total_hours']
    list_filter = ['status', 'priority', 'project']
    search_fields = ['title']


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['project', 'task', 'started_at', 'ended_at', 'duration_display', 'billed']
    list_filter = ['billed', 'project', 'owner']
    list_editable = ['billed']

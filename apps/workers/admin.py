from django.contrib import admin
from .models import Client, WorkerNode, Job, JobType

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'gpu_priority', 'api_priority', 'active')
    list_editable = ('gpu_priority', 'api_priority', 'active')

@admin.register(WorkerNode)
class WorkerNodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'worker_type', 'ip', 'online', 'active_jobs', 'last_seen')

@admin.register(JobType)
class JobTypeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'label', 'requires_gpu', 'requires_claude')

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('pk', 'client', 'job_type', 'priority', 'status', 'worker', 'created_at')
    list_filter  = ('status', 'client', 'job_type')

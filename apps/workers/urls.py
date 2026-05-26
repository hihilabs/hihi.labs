from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    path('download/', views.worker_download, name='worker_download'),

    # Client management
    path('clients/add/',          views.client_add,    name='client_add'),
    path('clients/<int:pk>/update/', views.client_update, name='client_update'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),

    # Worker node management
    path('nodes/<int:pk>/delete/', views.worker_delete, name='worker_delete'),

    # Job management (UI)
    path('jobs/submit/',           views.job_submit, name='job_submit'),
    path('jobs/<int:pk>/cancel/',  views.job_cancel, name='job_cancel'),

    # Live status (dashboard polling)
    path('api/status/', views.api_status, name='api_status'),

    # Worker process API
    path('api/heartbeat/',               views.api_heartbeat,    name='api_heartbeat'),
    path('api/jobs/pending/',            views.api_jobs_pending, name='api_jobs_pending'),
    path('api/jobs/<int:pk>/claim/',     views.api_job_claim,    name='api_job_claim'),
    path('api/jobs/<int:pk>/progress/',  views.api_job_progress, name='api_job_progress'),
    path('api/jobs/<int:pk>/complete/',  views.api_job_complete, name='api_job_complete'),
    path('api/jobs/<int:pk>/error/',     views.api_job_error,    name='api_job_error'),
    path('api/docker-agents/', views.api_docker_agents, name='api_docker_agents'),
    path('api/agent-exec/',    views.api_agent_exec,    name='api_agent_exec'),
    path('api/gpu-stats/',     views.api_gpu_stats,     name='api_gpu_stats'),
]

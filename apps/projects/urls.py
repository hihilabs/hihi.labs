from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_index, name='index'),
    path('new/', views.project_create, name='create'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('<int:pk>/update/', views.project_update, name='update'),

    # Tasks
    path('<int:project_pk>/tasks/new/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/update/', views.task_update, name='task_update'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('tasks/<int:pk>/suggest/', views.task_suggest, name='task_suggest'),

    # Timer
    path('timer/start/', views.timer_start, name='timer_start'),
    path('timer/stop/', views.timer_stop, name='timer_stop'),
    path('timer/status/', views.timer_status, name='timer_status'),
    path('time-log/', views.time_log, name='time_log'),
    path('time-log/<int:pk>/delete/', views.time_entry_delete, name='time_entry_delete'),

    # Global Tasks
    path('tasks/', views.global_tasks, name='global_tasks'),

    # Value Board
    path('value/', views.value_board, name='value_board'),
    path('<int:pk>/draft-invoice/', views.draft_invoice, name='draft_invoice'),

    # Project files
    path('<int:pk>/files/upload/', views.project_file_upload, name='file_upload'),
    path('<int:pk>/files/<int:file_pk>/delete/', views.project_file_delete, name='file_delete'),

    # Project notes
    path('<int:pk>/notes/new/', views.note_create, name='note_create'),
    path('<int:pk>/notes/<int:note_pk>/delete/', views.note_delete, name='note_delete'),
]

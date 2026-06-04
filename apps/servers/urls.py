from django.urls import path
from . import views

app_name = 'servers'

urlpatterns = [
    path('', views.index, name='index'),
    path('add/', views.server_add, name='server_add'),
    path('<int:pk>/delete/', views.server_delete, name='server_delete'),
    path('<int:pk>/ping/', views.server_ping, name='ping'),
    path('status/', views.fleet_status, name='fleet_status'),
    path('arch/', views.arch_view, name='arch'),
    path('stream/', views.status_stream, name='status_stream'),
    # Session check-in system
    path('sessions/', views.sessions_index, name='sessions'),
    path('sessions/checkin/', views.session_checkin, name='session_checkin'),
    path('sessions/checkout/', views.session_checkout, name='session_checkout'),
    path('sessions/heartbeat/', views.session_heartbeat, name='session_heartbeat'),
    # Terminal hook API (no login required — uses session_token)
    path('api/greet/', views.api_greet, name='api_greet'),
    path('api/identify/', views.api_identify, name='api_identify'),
]

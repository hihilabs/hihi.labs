from django.urls import path
from . import views

app_name = 'servers'

urlpatterns = [
    path('', views.index, name='index'),
    path('add/', views.server_add, name='server_add'),
    path('<int:pk>/delete/', views.server_delete, name='server_delete'),
    path('<int:pk>/ping/', views.server_ping, name='ping'),
]

from django.urls import path
from . import views

app_name = 'whiteboards'

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.create, name='create'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/save/', views.save, name='save'),
    path('<int:pk>/delete/', views.delete, name='delete'),
]

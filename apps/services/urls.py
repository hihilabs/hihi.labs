from django.urls import path
from . import views

app_name = 'services'
urlpatterns = [
    path('',                                       views.index,  name='index'),
    path('new/',                                   views.create, name='create'),
    path('<int:pk>/delete/',                       views.delete, name='delete'),
    path('<int:service_pk>/toggle/<int:project_pk>/', views.toggle, name='toggle'),
]

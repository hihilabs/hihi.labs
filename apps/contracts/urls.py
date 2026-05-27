from django.urls import path
from . import views

app_name = 'contracts'
urlpatterns = [
    path('',               views.index,  name='index'),
    path('new/',           views.create, name='create'),
    path('<int:pk>/',      views.detail, name='detail'),
    path('<int:pk>/update/', views.update, name='update'),
    path('<int:pk>/delete/', views.delete, name='delete'),
]

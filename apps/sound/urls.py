from django.urls import path
from . import views

app_name = 'sound'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.track_upload, name='track_upload'),
    path('<int:pk>/', views.track_detail, name='track_detail'),
    path('<int:pk>/update/', views.track_update, name='track_update'),
    path('<int:pk>/delete/', views.track_delete, name='track_delete'),
    path('<int:pk>/comments/add/', views.comment_add, name='comment_add'),
    path('<int:pk>/comments/<int:comment_pk>/delete/', views.comment_delete, name='comment_delete'),
]

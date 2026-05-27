from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('', views.index, name='index'),
    path('oauth/start/', views.oauth_start, name='oauth_start'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('oauth/disconnect/', views.oauth_disconnect, name='oauth_disconnect'),
    path('api/browse/', views.browse_api, name='browse_api'),
    path('link/', views.link_folder, name='link_folder'),
    path('unlink/<int:pk>/', views.unlink_folder, name='unlink_folder'),
]

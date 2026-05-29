from django.urls import path
from . import views

app_name = 'among_us'

urlpatterns = [
    path('', views.index, name='index'),
    path('download/cfg/', views.download_cfg, name='download_cfg'),
    path('download/family/', views.download_family_cfg, name='download_family_cfg'),
]

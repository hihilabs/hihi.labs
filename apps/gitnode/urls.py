from django.urls import path
from . import views

app_name = 'gitnode'

urlpatterns = [
    path('',                      views.index,       name='index'),
    path('scoop/',                views.scoop_all,   name='scoop_all'),
    path('<int:pk>/status/',      views.repo_status, name='status'),
    path('<int:pk>/scoop/',       views.repo_scoop,  name='scoop'),
    path('<int:pk>/deploy/',      views.repo_deploy, name='deploy'),
]

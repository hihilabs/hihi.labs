from django.urls import path
from . import views

app_name = 'ops'

urlpatterns = [
    path('',                         views.panel,           name='panel'),
    path('system/',                  views.system_panel,    name='system'),
    path('cmd/',                     views.run_cmd,          name='run_cmd'),
    path('deploy/',                  views.deploy_webhook,   name='deploy_webhook'),
    path('ticket/create/',           views.create_ticket,    name='create_ticket'),
    path('ticket/<int:pk>/update/',  views.update_ticket,    name='update_ticket'),
    path('repos/check/',             views.check_all_repos,  name='check_all_repos'),
]

from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('',                           views.admin_view,        name='admin'),
    path('client/<int:client_pk>/save/', views.client_config_save, name='client_save'),
    path('footer/<str:footer_type>/save/', views.footer_save,   name='footer_save'),
    path('submit/',                    views.ticket_submit,      name='ticket_submit'),
]

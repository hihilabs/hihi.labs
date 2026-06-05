from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Staff admin
    path('',                                    views.admin_view,         name='admin'),
    path('client/<int:client_pk>/save/',        views.client_config_save, name='client_save'),
    path('client/<int:client_pk>/preview/',     views.portal_preview,     name='preview'),
    path('client/<int:client_pk>/regen-token/', views.regenerate_token,   name='regen_token'),
    path('footer/<str:footer_type>/save/',      views.footer_save,        name='footer_save'),
    path('submit/',                             views.ticket_submit,       name='ticket_submit'),

    # Public client portal — token-gated, no login required
    path('view/<uuid:token>/',                  views.client_portal,      name='client_portal'),
]

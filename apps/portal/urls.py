from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Staff admin
    path('',                                        views.admin_view,              name='admin'),
    path('client/<int:client_pk>/save/',            views.client_config_save,      name='client_save'),
    path('client/<int:client_pk>/preview/',         views.portal_preview,          name='preview'),
    path('client/<int:client_pk>/regen-token/',     views.regenerate_token,        name='regen_token'),
    path('client/<int:client_pk>/send-invite/',     views.send_invite,             name='send_invite'),
    path('footer/<str:footer_type>/save/',          views.footer_save,             name='footer_save'),
    path('submit/',                                 views.ticket_submit,           name='ticket_submit'),

    # Public client portal — token-gated, no login required
    path('view/<uuid:token>/',                      views.client_portal,           name='client_portal'),
    path('view/<uuid:token>/voice/',                views.portal_voice_transcribe, name='portal_voice'),
    path('view/<uuid:token>/threads/new/',          views.portal_thread_new,       name='portal_thread_new'),
    path('view/<uuid:token>/threads/<int:thread_pk>/',         views.portal_thread_detail, name='portal_thread_detail'),
    path('view/<uuid:token>/threads/<int:thread_pk>/reply/',   views.portal_thread_reply,  name='portal_thread_reply'),
    path('view/<uuid:token>/tasks/<int:task_pk>/assign/',     views.portal_task_assign,  name='portal_task_assign'),

    # Per-contact portal ("My Tasks") -- groundwork for individual contact logins
    path('contact/<uuid:token>/',                             views.contact_portal,      name='contact_portal'),
    path('contact/<uuid:token>/tasks/<int:task_pk>/status/',  views.contact_task_status, name='contact_task_status'),
]

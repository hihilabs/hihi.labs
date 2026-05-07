from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.index, name='index'),
    path('upgrade/', views.upgrade, name='upgrade'),
    path('phantom/submit/', views.phantom_submit, name='phantom_submit'),
    path('helium/submit/', views.helium_submit, name='helium_submit'),
    path('stripe/session/', views.stripe_create_session, name='stripe_session'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('admin/helium/<int:payment_id>/confirm/', views.admin_confirm_helium, name='admin_confirm_helium'),
]

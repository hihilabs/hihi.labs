from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from hihilabs import views as core_views

urlpatterns = [
    path('', lambda r: redirect('/dashboard/', permanent=False)),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    path('search/', core_views.power_search, name='power_search'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('ai/', include('apps.claude_ai.urls', namespace='ai')),
    path('projects/', include('apps.projects.urls', namespace='projects')),
    path('sound/', include('apps.sound.urls', namespace='sound')),
    path('servers/', include('apps.servers.urls', namespace='servers')),
    path('tax/', include('apps.tax.urls', namespace='tax')),
    path('billing/', include('apps.billing.urls', namespace='billing')),
    path('subscriptions/', include('apps.subscriptions.urls', namespace='subscriptions')),
    path('messaging/', include('apps.messaging.urls', namespace='messaging')),
    path('modules/', include('apps.modules.urls', namespace='modules')),
    path('workers/', include('apps.workers.urls', namespace='workers')),
    path('ops/', include('apps.ops.urls')),
    path('clients/', include('apps.clients.urls', namespace='clients')),
    path('proposals/', include('apps.proposals.urls', namespace='proposals')),
    path('contracts/', include('apps.contracts.urls', namespace='contracts')),
    path('services/', include('apps.services.urls', namespace='services')),
    path('files/', include('apps.files.urls', namespace='files')),
    path('wiki/', include('apps.wiki.urls', namespace='wiki')),
    path('whiteboards/', include('apps.whiteboards.urls', namespace='whiteboards')),
    # PWA
    path('sw.js',           core_views.service_worker,   name='service_worker'),
    path('offline/',        core_views.offline,          name='offline'),
    path('push/vapid-key/', core_views.push_vapid_key,   name='push_vapid_key'),
    path('push/subscribe/', core_views.push_subscribe,   name='push_subscribe'),
    path('push/unsubscribe/', core_views.push_unsubscribe, name='push_unsubscribe'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

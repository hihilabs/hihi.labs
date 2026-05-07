from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('thread/new/', views.thread_new, name='thread_new'),
    path('thread/<int:pk>/', views.thread_detail, name='thread_detail'),
    path('thread/<int:pk>/reply/', views.thread_reply, name='thread_reply'),
    path('notifications/', views.notifications_api, name='notifications_api'),
    path('notifications/read-all/', views.notifications_read_all, name='notifications_read_all'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
    path('unread/', views.unread_count, name='unread_count'),
    path('email-accounts/', views.email_accounts, name='email_accounts'),
    path('email-accounts/add/', views.email_account_add, name='email_account_add'),
    path('email-accounts/<int:account_id>/sync/', views.email_sync, name='email_sync'),
]

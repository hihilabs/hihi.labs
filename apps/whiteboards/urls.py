from django.urls import path
from . import views

app_name = 'whiteboards'

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.create, name='create'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/save/', views.save, name='save'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:pk>/rtc-token/', views.rtc_token, name='rtc_token'),
    path('<int:pk>/speech/', views.speech, name='speech'),
    path('<int:pk>/sandbox/', views.sandbox_state, name='sandbox_state'),
    path('<int:pk>/sandbox/new/', views.sandbox_new, name='sandbox_new'),
    path('<int:pk>/sandbox/<int:sb_pk>/stop/', views.sandbox_stop, name='sandbox_stop'),
    path('<int:pk>/sandbox/<int:sb_pk>/files/', views.sandbox_files, name='sandbox_files'),
    path('<int:pk>/module/<int:module_pk>/run/', views.room_module_run, name='room_module_run'),
]

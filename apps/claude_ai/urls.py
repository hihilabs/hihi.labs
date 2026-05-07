from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    # Chat
    path('', views.chat_index, name='index'),
    path('chat/new/', views.chat_new, name='chat_new'),
    path('chat/<int:pk>/', views.chat_detail, name='chat'),
    path('chat/<int:pk>/send/', views.chat_send, name='chat_send'),
    path('chat/<int:pk>/stream/', views.chat_stream, name='chat_stream'),
    path('chat/<int:pk>/delete/', views.chat_delete, name='chat_delete'),

    # Templates
    path('templates/', views.templates_index, name='templates'),
    path('templates/<int:pk>/run/', views.template_run, name='template_run'),
    path('templates/<int:pk>/stream/', views.template_stream, name='template_stream'),

    # Documents
    path('documents/', views.documents_index, name='documents'),
    path('documents/<int:pk>/', views.document_detail, name='document'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),

    # Voice
    path('voice/', views.voice_index, name='voice'),
    path('voice/transcribe/', views.voice_transcribe, name='voice_transcribe'),
    path('voice/<int:pk>/delete/', views.voice_delete, name='voice_delete'),
]

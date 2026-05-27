from django.urls import path
from . import views

app_name = 'wiki'

urlpatterns = [
    path('', views.index, name='index'),
    path('sections/new/', views.section_create, name='section_create'),
    path('sections/<int:pk>/update/', views.section_update, name='section_update'),
    path('sections/<int:pk>/delete/', views.section_delete, name='section_delete'),
    path('sections/<int:section_pk>/notes/new/', views.note_create, name='note_create'),
    path('notes/<int:pk>/update/', views.note_update, name='note_update'),
    path('notes/<int:pk>/delete/', views.note_delete, name='note_delete'),
]

from django.urls import path
from . import views

app_name = 'proposals'
urlpatterns = [
    path('',               views.index,     name='index'),
    path('new/',           views.create,    name='create'),
    path('<int:pk>/',      views.detail,    name='detail'),
    path('<int:pk>/update/', views.update,  name='update'),
    path('<int:pk>/delete/', views.delete,  name='delete'),
    path('<int:pk>/lines/',  views.line_save, name='line_save'),
]

from django.urls import path
from . import views

app_name = 'clients'
urlpatterns = [
    path('',                                 views.index,          name='index'),
    path('new/',                             views.create,         name='create'),
    path('<int:pk>/',                        views.detail,         name='detail'),
    path('<int:pk>/update/',                 views.update,         name='update'),
    path('<int:pk>/delete/',                 views.delete,         name='delete'),
    path('<int:pk>/contacts/new/',           views.contact_create, name='contact_create'),
    path('<int:pk>/contacts/<int:contact_pk>/delete/', views.contact_delete, name='contact_delete'),
]

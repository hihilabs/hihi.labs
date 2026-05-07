from django.urls import path
from . import views

app_name = 'tax'

urlpatterns = [
    path('', views.index, name='index'),
    path('add/', views.expense_add, name='expense_add'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('<int:pk>/toggle/', views.expense_toggle, name='expense_toggle'),
    path('export/', views.expense_csv, name='expense_csv'),
]

from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.invoice_new, name='invoice_new'),
    path('<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('<int:pk>/add-line/', views.invoice_add_line, name='invoice_add_line'),
    path('<int:pk>/lines/<int:line_pk>/delete/', views.invoice_delete_line, name='invoice_delete_line'),
    path('<int:pk>/mark-sent/', views.invoice_mark_sent, name='invoice_mark_sent'),
    path('<int:pk>/mark-paid/', views.invoice_mark_paid, name='invoice_mark_paid'),
    path('<int:pk>/void/', views.invoice_void, name='invoice_void'),
    path('<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
]

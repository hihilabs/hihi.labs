from django.urls import path
from . import views

app_name = 'pepperjuice'

urlpatterns = [
    path('',                          views.dashboard,              name='dashboard'),
    path('bills/',                    views.bills_view,             name='bills'),
    path('bills/save/',               views.bill_save,              name='bill_save'),
    path('bills/<int:pk>/delete/',    views.bill_delete,            name='bill_delete'),
    path('bills/<int:pk>/paid/',      views.bill_mark_paid,         name='bill_mark_paid'),
    path('goals/',                    views.goals_view,             name='goals'),
    path('goals/save/',               views.goal_save,              name='goal_save'),
    path('goals/<int:pk>/delete/',    views.goal_delete,            name='goal_delete'),
    path('accounts/',                 views.accounts_view,          name='accounts'),
    path('accounts/sync/',            views.sync_accounts,          name='sync_accounts'),
    path('accounts/<int:pk>/toggle/',  views.account_toggle_business, name='account_toggle_business'),
    path('accounts/<int:pk>/subtype/', views.account_set_subtype,     name='account_set_subtype'),
    path('connect/',                  views.connect_view,           name='connect'),
    path('disconnect/',               views.disconnect,             name='disconnect'),
]

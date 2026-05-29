from django.contrib import admin
from .models import SequenceConnection, CachedAccount, Bill, BillPayment, SavingsGoal


@admin.register(SequenceConnection)
class SequenceConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'display_name', 'last_sync', 'connected_at']
    readonly_fields = ['connected_at']


@admin.register(CachedAccount)
class CachedAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'account_type', 'balance_display', 'is_business', 'synced_at']
    list_filter = ['account_type', 'is_business']


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'amount_display', 'due_day', 'category', 'is_auto_pay', 'is_business', 'is_active']
    list_filter = ['category', 'is_auto_pay', 'is_business', 'is_active']


@admin.register(BillPayment)
class BillPaymentAdmin(admin.ModelAdmin):
    list_display = ['bill', 'paid_date', 'amount_cents']
    list_filter = ['paid_date']


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'goal_type', 'progress_pct', 'target_cents', 'is_active']
    list_filter = ['goal_type', 'is_active']

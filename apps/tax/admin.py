from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'vendor', 'amount', 'category', 'is_deductible', 'owner')
    list_filter = ('category', 'is_deductible')
    search_fields = ('vendor', 'description')
    list_editable = ('is_deductible',)

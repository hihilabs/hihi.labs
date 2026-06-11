from django.contrib import admin
from .models import Invoice, InvoiceLine, CostSettings, ProjectExpense


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ('amount',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'client_name', 'status', 'issued_date', 'due_date')
    list_filter = ('status',)
    inlines = [InvoiceLineInline]


@admin.register(CostSettings)
class CostSettingsAdmin(admin.ModelAdmin):
    list_display = ('labor_cost_per_hour', 'overhead_monthly', 'target_margin_pct', 'updated_at')

    def has_add_permission(self, request):
        return not CostSettings.objects.exists()


@admin.register(ProjectExpense)
class ProjectExpenseAdmin(admin.ModelAdmin):
    list_display = ('project', 'description', 'kind', 'amount', 'date')
    list_filter = ('kind',)

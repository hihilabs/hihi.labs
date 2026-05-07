from django.contrib import admin
from .models import Invoice, InvoiceLine


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ('amount',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'client_name', 'status', 'issued_date', 'due_date')
    list_filter = ('status',)
    inlines = [InvoiceLineInline]

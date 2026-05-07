from django.contrib import admin
from django.utils.html import format_html
from .models import Plan, Subscription, PaymentRecord


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'price_usd', 'price_sol', 'price_hnt', 'feature_list', 'is_active')
    list_editable = ('is_active',)

    def feature_list(self, obj):
        return ', '.join(obj.features or [])


class PaymentRecordInline(admin.TabularInline):
    model = PaymentRecord
    extra = 0
    readonly_fields = ('gateway', 'amount_usd', 'amount_crypto', 'currency', 'tx_hash', 'status', 'paid_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'gateway', 'current_period_end')
    list_filter = ('status', 'gateway', 'plan')
    search_fields = ('user__username', 'user__email', 'stripe_customer_id')
    inlines = [PaymentRecordInline]


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'gateway', 'currency', 'amount_display', 'status', 'confirm_action', 'paid_at')
    list_filter = ('gateway', 'status', 'currency')
    readonly_fields = ('created_at',)

    def amount_display(self, obj):
        if obj.amount_usd:
            return f'${obj.amount_usd}'
        return f'{obj.amount_crypto} {obj.currency}'
    amount_display.short_description = 'Amount'

    def confirm_action(self, obj):
        if obj.gateway == 'helium' and obj.status == 'pending':
            return format_html(
                '<a class="button" href="/subscriptions/admin/helium/{}/confirm/" style="background:#4caf50;color:#fff;padding:3px 10px;border-radius:4px;">Confirm</a>',
                obj.pk
            )
        return obj.get_status_display()
    confirm_action.short_description = 'Action'

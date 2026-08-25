import json

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.orders.models import PaymentTransaction

TXN_STATUS_COLORS = {
    PaymentTransaction.Status.PENDING: 'warning',
    PaymentTransaction.Status.SUCCESS: 'success',
    PaymentTransaction.Status.FAILED: 'danger',
}


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    """
    Read-only by design: transactions are only ever written by the checkout
    flow (CheckoutInitiateView / PaymentCallbackView). This view exists so
    support/finance can search and audit gateway attempts without having to
    open every order individually - e.g. "did we ever get a callback for
    this transid the customer is asking about".
    """

    list_display = ('order_link', 'gateway', 'status_badge', 'amount_display', 'authority', 'created_at', 'verified_at')
    list_filter = ('gateway', 'status', 'created_at')
    search_fields = ('order__order_number', 'authority')
    date_hierarchy = 'created_at'
    list_select_related = ('order',)
    ordering = ('-id',)

    readonly_fields = (
        'order',
        'gateway',
        'authority',
        'amount',
        'status',
        'raw_response_pretty',
        'created_at',
        'verified_at',
    )
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_('order'))
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order_id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)

    @display(description=_('status'), label=True, ordering='status')
    def status_badge(self, obj):
        return obj.get_status_display(), TXN_STATUS_COLORS.get(obj.status, 'info')

    @display(description=_('amount'), ordering='amount')
    def amount_display(self, obj):
        return f'{obj.amount:,} تومان'

    @display(description=_('raw gateway response'))
    def raw_response_pretty(self, obj):
        pretty = json.dumps(obj.raw_response, indent=2, ensure_ascii=False)
        return format_html('<pre style="white-space: pre-wrap">{}</pre>', pretty)
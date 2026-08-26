from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms.models import BaseInlineFormSet
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.catalog.models import ProductVariant
from apps.orders.models import Order, OrderItem, PaymentTransaction
from apps.orders.services.checkout_service import (
    apply_order_item_delta,
    cancel_order,
    expire_order,
    mark_order_paid_manually,
    mark_order_refunded,
    recalculate_order_totals,
    variant_allocation_cap,
)

STATUS_COLORS = {
    Order.Status.PENDING_PAYMENT: 'warning',
    Order.Status.PAID: 'success',
    Order.Status.CANCELLED: 'danger',
    Order.Status.EXPIRED: 'danger',
    Order.Status.REFUNDED: 'info',
}

SHIPPING_STATUS_COLORS = {
    Order.ShippingStatus.PENDING: 'warning',
    Order.ShippingStatus.PROCESSING: 'info',
    Order.ShippingStatus.SHIPPED: 'primary',
    Order.ShippingStatus.DELIVERED: 'success',
    Order.ShippingStatus.RETURNED: 'danger',
}

TXN_STATUS_COLORS = {
    PaymentTransaction.Status.PENDING: 'warning',
    PaymentTransaction.Status.SUCCESS: 'success',
    PaymentTransaction.Status.FAILED: 'danger',
}

# Item edits only make sense for these two states - a cancelled/expired
# order already released its reservation (nothing to adjust against), and a
# refunded order's stock story is handled separately by mark_order_refunded.
ITEM_EDITABLE_STATUSES = (Order.Status.PENDING_PAYMENT, Order.Status.PAID)


class OrderItemInlineFormSet(BaseInlineFormSet):
    """
    Validates the WHOLE set of item changes against real stock before
    anything is written - this is what makes it safe to let admins add,
    resize, or remove order lines by hand. Runs during is_valid(), so a
    rejected change shows as a normal red form error, not a 500.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        order = self.instance
        if order.pk and order.status not in ITEM_EDITABLE_STATUSES:
            # belt-and-suspenders: the inline is also set read-only for
            # these statuses (see get_readonly_fields), this just covers
            # anyone hitting the endpoint directly.
            raise ValidationError(_('Items can only be edited while an order is pending payment or paid.'))

        order_is_paid = order.status == Order.Status.PAID

        requested = {}
        for form in self.forms:
            if not getattr(form, 'cleaned_data', None):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            variant = form.cleaned_data.get('variant')
            quantity = form.cleaned_data.get('quantity')
            if not variant or not quantity:
                continue
            requested[variant.id] = requested.get(variant.id, 0) + quantity

        existing = dict(order.items.values_list('variant_id', 'quantity')) if order.pk else {}

        with transaction.atomic():
            variants = {v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=requested.keys())}
            for variant_id, new_qty in requested.items():
                variant = variants[variant_id]
                old_qty = existing.get(variant_id, 0)
                cap = variant_allocation_cap(variant, current_order_qty=old_qty, order_is_paid=order_is_paid)
                if new_qty > cap:
                    raise ValidationError(
                        _('Not enough stock for %(variant)s: requested %(requested)s, max allowed %(cap)s.')
                        % {'variant': str(variant), 'requested': new_qty, 'cap': cap}
                    )


class OrderItemInline(TabularInline):
    model = OrderItem
    formset = OrderItemInlineFormSet
    extra = 0
    tab = True
    fields = ('variant', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',)  # always derived, never hand-entered

    def get_readonly_fields(self, request, obj=None):
        if obj is None or obj.status in ITEM_EDITABLE_STATUSES:
            return self.readonly_fields
        # locked read-only view for cancelled/expired/refunded orders
        return ('variant', 'quantity', 'unit_price', 'total_price')

    def has_add_permission(self, request, obj=None):
        return obj is None or obj.status in ITEM_EDITABLE_STATUSES

    def has_change_permission(self, request, obj=None):
        return obj is None or obj.status in ITEM_EDITABLE_STATUSES

    def has_delete_permission(self, request, obj=None):
        return obj is not None and obj.status in ITEM_EDITABLE_STATUSES


class PaymentTransactionInline(TabularInline):
    model = PaymentTransaction
    extra = 0
    can_delete = False
    tab = True
    fields = ('gateway', 'txn_status_badge', 'authority', 'amount', 'created_at', 'verified_at')
    readonly_fields = ('gateway', 'txn_status_badge', 'authority', 'amount', 'created_at', 'verified_at')

    def has_add_permission(self, request, obj=None):
        # transactions are only ever created by the checkout/payment flow,
        # never by hand - a fake transaction row would be misleading, since
        # mark_order_paid_manually intentionally doesn't create one.
        return False

    @display(description=_('status'), label=TXN_STATUS_COLORS)
    def txn_status_badge(self, obj):
        return obj.status, obj.get_status_display()


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        'order_number',
        'user_display',
        'status_badge',
        'shipping_status_badge',
        'total_amount_display',
        'time_left_display',
        'created_at',
    )
    list_filter = ('status', 'shipping_status', 'created_at')
    search_fields = ('order_number', 'tracking_code', 'user__phone', 'user__email')
    date_hierarchy = 'created_at'
    list_select_related = ('user', 'address')
    ordering = ('-id',)
    inlines = (OrderItemInline, PaymentTransactionInline)
    actions = ('action_cancel_orders', 'action_expire_orders', 'action_mark_paid', 'action_mark_refunded')

    # `status` is deliberately view-only here - it only ever changes through
    # the actions below, each of which keeps stock bookkeeping consistent
    # with the transition. Letting an admin free-type a new status in this
    # form (in the same submit as editing items) would let the item-formset
    # validation and the status change disagree about which stock pool
    # ("reserved" vs "real") an edit should draw from - splitting status
    # changes into their own explicit action removes that whole class of
    # bug rather than trying to detect it.
    readonly_fields = (
        'token',
        'order_number',
        'status',
        'subtotal_amount',
        'total_amount',
        'created_at',
        'updated_at',
        'paid_at',
    )

    fieldsets = (
        (
            _('order'),
            {
                'fields': (
                    ('order_number', 'token'),
                    'user',
                    'address',
                    ('status', 'shipping_status'),
                    'expires_at',
                )
            },
        ),
        (
            _('amounts'),
            {
                'fields': (
                    ('subtotal_amount', 'shipping_amount'),
                    ('discount_amount', 'total_amount'),
                ),
                'description': _(
                    'subtotal and total are recalculated automatically from the order items '
                    'below whenever you save - only shipping and discount are hand-edited here.'
                ),
            },
        ),
        (
            _('shipping'),
            {
                'fields': ('tracking_code', 'shipping_company', 'shipped_at', 'delivered_at'),
                'classes': ('collapse',),
            },
        ),
        (
            _('notes'),
            {
                'fields': ('customer_note', 'admin_note'),
                'classes': ('collapse',),
            },
        ),
        (
            _('timestamps'),
            {
                'fields': ('paid_at', 'created_at', 'updated_at'),
                'classes': ('collapse',),
            },
        ),
    )

    @display(description=_('customer'))
    def user_display(self, obj):
        return str(obj.user)

    @display(description=_('status'), label=STATUS_COLORS, ordering='status')
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @display(description=_('shipping'), label=SHIPPING_STATUS_COLORS, ordering='shipping_status')
    def shipping_status_badge(self, obj):
        return obj.shipping_status, obj.get_shipping_status_display()

    @display(description=_('total'), ordering='total_amount')
    def total_amount_display(self, obj):
        return f'{obj.total_amount:,} تومان'

    @display(description=_('time left'))
    def time_left_display(self, obj):
        if obj.status != Order.Status.PENDING_PAYMENT:
            return '—'
        remaining = obj.expires_at - timezone.now()
        if remaining.total_seconds() <= 0:
            return format_html('<span style="color: var(--color-danger-600)">{}</span>', _('expired (pending sweep)'))
        minutes = int(remaining.total_seconds() // 60)
        seconds = int(remaining.total_seconds() % 60)
        return f'{minutes}m {seconds}s'

    def save_formset(self, request, form, formset, change):
        if formset.model is not OrderItem:
            return super().save_formset(request, form, formset, change)

        order = form.instance
        order_is_paid = order.status == Order.Status.PAID

        # snapshot BEFORE any writes from this formset
        old_quantities = dict(order.items.values_list('variant_id', 'quantity'))

        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            old_qty = old_quantities.get(obj.variant_id, 0)
            apply_order_item_delta(variant_id=obj.variant_id, delta=-old_qty, order_is_paid=order_is_paid)
            obj.delete()

        for instance in instances:
            is_new = instance.pk is None
            old_qty = 0 if is_new else old_quantities.get(instance.variant_id, 0)
            if not instance.unit_price:
                instance.unit_price = instance.variant.price
            instance.total_price = instance.quantity * instance.unit_price

            delta = instance.quantity - old_qty
            apply_order_item_delta(variant_id=instance.variant_id, delta=delta, order_is_paid=order_is_paid)
            instance.order = order
            instance.save()

        formset.save_m2m()
        recalculate_order_totals(order.pk)

    @admin.action(description=_('Cancel selected orders and release reserved stock'))
    def action_cancel_orders(self, request, queryset):
        count = 0
        for order in queryset.filter(status=Order.Status.PENDING_PAYMENT):
            cancel_order(order.id)
            count += 1
        self.message_user(request, f'{count} order(s) cancelled and stock released.', level=messages.SUCCESS)

    @admin.action(description=_('Force-expire selected orders now'))
    def action_expire_orders(self, request, queryset):
        count = 0
        for order in queryset.filter(status=Order.Status.PENDING_PAYMENT):
            expire_order(order.id)
            count += 1
        self.message_user(request, f'{count} order(s) expired and stock released.', level=messages.SUCCESS)

    @admin.action(description=_('Mark as paid manually (offline / bank transfer)'))
    def action_mark_paid(self, request, queryset):
        count = 0
        for order in queryset.filter(status=Order.Status.PENDING_PAYMENT):
            mark_order_paid_manually(order.id)
            count += 1
        self.message_user(
            request,
            f'{count} order(s) marked paid without gateway verification - double check these.',
            level=messages.WARNING,
        )

    @admin.action(description=_('Mark as refunded (does not auto-restock or call the gateway)'))
    def action_mark_refunded(self, request, queryset):
        count = 0
        for order in queryset.filter(status=Order.Status.PAID):
            mark_order_refunded(order.id)
            count += 1
        self.message_user(
            request,
            f'{count} order(s) marked refunded. Remember to restock and process the refund with the gateway separately.',
            level=messages.WARNING,
        )
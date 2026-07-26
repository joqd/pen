from django.contrib import admin, messages
from django.contrib.admin import display
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline

from apps.orders.models import Order, OrderItem


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0

    autocomplete_fields = ('variant',)

    fields = (
        'variant',
        'quantity',
        'unit_price',
        'total_price',
    )

    readonly_fields = ('total_price',)


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    inlines = (OrderItemInline,)

    actions = (
        'mark_as_paid',
        'mark_as_shipped',
    )

    autocomplete_fields = (
        'user',
        'address',
    )

    list_select_related = (
        'user',
        'address',
    )

    search_fields = (
        'order_number',
        'tracking_code',
        'user__phone',
        'user__full_name',
    )

    list_filter = (
        'status',
        'shipping_status',
        'created_at',
        'paid_at',
    )

    list_display = (
        'order_number',
        'user',
        'item_count',
        'total_amount',
        'status',
        'shipping_status',
        'tracking_code',
        'created_at',
    )

    readonly_fields = (
        'order_number',
        'subtotal_amount',
        'discount_amount',
        'shipping_amount',
        'total_amount',
        'created_at',
        'updated_at',
        'paid_at',
        'shipped_at',
        'delivered_at',
    )

    fieldsets = (
        (
            _('order'),
            {
                'classes': ('tab',),
                'fields': (
                    'order_number',
                    'user',
                    'address',
                    'status',
                    'shipping_status',
                ),
            },
        ),
        (
            _('amounts'),
            {
                'classes': ('tab',),
                'fields': (
                    'subtotal_amount',
                    'discount_amount',
                    'shipping_amount',
                    'total_amount',
                ),
            },
        ),
        (
            _('shipping'),
            {
                'classes': ('tab',),
                'fields': (
                    'shipping_company',
                    'tracking_code',
                    'shipped_at',
                    'delivered_at',
                ),
            },
        ),
        (
            _('notes'),
            {
                'classes': ('tab',),
                'fields': (
                    'customer_note',
                    'admin_note',
                ),
            },
        ),
        (
            _('payment'),
            {
                'classes': ('tab',),
                'fields': (
                    'expires_at',
                    'paid_at',
                ),
            },
        ),
        (
            _('Metadata'),
            {
                'classes': ('tab',),
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                'user',
                'address',
            )
            .prefetch_related(
                'items',
            )
        )

    @display(description=_('items'))
    def item_count(self, obj):
        return obj.items.count()

    @admin.action(description=_('mark selected orders as paid'))
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(
            status=Order.Status.PAID,
            paid_at=timezone.now(),
        )

        self.message_user(
            request,
            f'{updated} orders marked as paid.',
            messages.SUCCESS,
        )

    @admin.action(description=_('mark selected orders as shipped'))
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(
            shipping_status=Order.ShippingStatus.SHIPPED,
            shipped_at=timezone.now(),
        )

        self.message_user(
            request,
            f'{updated} orders marked as shipped.',
            messages.SUCCESS,
        )


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    autocomplete_fields = (
        'order',
        'variant',
    )

    list_select_related = (
        'order',
        'variant',
    )

    search_fields = (
        'order__order_number',
        'variant__sku',
    )

    list_display = (
        'order',
        'variant',
        'quantity',
        'unit_price',
        'total_price',
    )

    readonly_fields = ('total_price',)

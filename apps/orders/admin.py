from django.contrib import admin
from django.contrib.admin import display
from django.db.models import Count, Sum, F
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from unfold.admin import ModelAdmin, TabularInline

from apps.orders.models import Cart, CartItem, Order, OrderItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ('variant',)
    fields = ('variant', 'quantity', 'unit_price', 'line_total')
    readonly_fields = ('unit_price', 'line_total')

    @display(description=_('unit price'))
    def unit_price(self, obj):
        if not obj.pk:
            return '—'
        return f'{obj.variant.price:,}'

    @display(description=_('total'))
    def line_total(self, obj):
        if not obj.pk:
            return '—'
        return f'{obj.variant.price * obj.quantity:,}'
    

@admin.register(Cart)
class CartAdmin(ModelAdmin):
    inlines = (CartItemInline,)
    autocomplete_fields = ('user',)
    search_fields = ('user__phone', 'token')
    list_display = ('owner', 'item_count', 'total_quantity', 'total_price', 'guest_status', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('token', 'created_at', 'updated_at')
    fieldsets = (
        (
            _('General'),
            {
                'fields': (
                    'user',
                    'token',
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
            .select_related('user')
            .annotate(
                items_count=Count('items'),
                quantity_sum=Sum('items__quantity'),
                total_sum=Sum(
                    F('items__quantity') *
                    F('items__variant__price')
                ),
            )
        )

    @display(description=_('owner'))
    def owner(self, obj):
        if obj.user:
            return obj.user.phone

        return _('guest')

    @display(
        description=_('items'),
        ordering='items_count',
    )
    def item_count(self, obj):
        return obj.items_count or 0

    @display(
        description=_('quantity'),
        ordering='quantity_sum',
    )
    def total_quantity(self, obj):
        return obj.quantity_sum or 0

    @display(
        description=_('total'),
        ordering='total_sum',
    )
    def total_price(self, obj):
        return f'{(obj.total_sum or 0):,}'
    
    @display(description=_('is guest'))
    def guest_status(self, obj):
        return _('Yes') if obj.is_guest else _('No')
    

@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    autocomplete_fields = ('cart', 'variant')
    list_select_related = ('cart', 'variant', 'variant__product', 'variant__size')
    search_fields = ('variant__sku', 'variant__product__title', 'cart__user__phone')
    list_display = ('id', 'cart_owner', 'product', 'size', 'quantity', 'price', 'line_total', 'created_at')
    readonly_fields = ('created_at',)

    @display(description=_('owner'))
    def cart_owner(self, obj):
        if obj.cart.user:
            return obj.cart.user.phone

        return _('Guest')

    @display(description=_('product'))
    def product(self, obj):
        return obj.variant.product.title

    @display(description=_('size'))
    def size(self, obj):
        return obj.variant.size.name

    @display(description=_('price'))
    def price(self, obj):
        return f'{obj.variant.price:,}'

    @display(description=_('total'))
    def line_total(self, obj):
        return f'{obj.variant.price * obj.quantity:,}'
    

class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0

    autocomplete_fields = (
        "variant",
    )

    fields = (
        "variant",
        "quantity",
        "unit_price",
        "total_price",
    )

    readonly_fields = (
        "total_price",
    )
    

@admin.register(Order)
class OrderAdmin(ModelAdmin):

    inlines = (
        OrderItemInline,
    )

    actions = (
        "mark_as_paid",
        "mark_as_shipped",
    )

    autocomplete_fields = (
        "user",
        "address",
    )

    list_select_related = (
        "user",
        "address",
    )

    search_fields = (
        "order_number",
        "tracking_code",
        "user__phone",
        "user__full_name",
    )

    list_filter = (
        "status",
        "shipping_status",
        "created_at",
        "paid_at",
    )

    list_display = (
        "order_number",
        "user",
        "item_count",
        "total_amount",
        "status",
        "shipping_status",
        "tracking_code",
        "created_at",
    )

    readonly_fields = (
        "order_number",
        "subtotal_amount",
        "discount_amount",
        "shipping_amount",
        "total_amount",
        "created_at",
        "updated_at",
        "paid_at",
        "shipped_at",
        "delivered_at",
    )

    fieldsets = (
        (
            _("Order"),
            {
                "classes": ("tab",),
                "fields": (
                    "order_number",
                    "user",
                    "address",
                    "status",
                    "shipping_status",
                ),
            },
        ),
        (
            _("Amounts"),
            {
                "classes": ("tab",),
                "fields": (
                    "subtotal_amount",
                    "discount_amount",
                    "shipping_amount",
                    "total_amount",
                ),
            },
        ),
        (
            _("Shipping"),
            {
                "classes": ("tab",),
                "fields": (
                    "shipping_company",
                    "tracking_code",
                    "shipped_at",
                    "delivered_at",
                ),
            },
        ),
        (
            _("Notes"),
            {
                "classes": ("tab",),
                "fields": (
                    "customer_note",
                    "admin_note",
                ),
            },
        ),
        (
            _("Payment"),
            {
                "classes": ("tab",),
                "fields": (
                    "expires_at",
                    "paid_at",
                ),
            },
        ),
        (
            _("Metadata"),
            {
                "classes": ("tab",),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "user",
                "address",
            )
            .prefetch_related(
                "items",
            )
        )

    @display(description=_("items"))
    def item_count(self, obj):
        return obj.items.count()
    
    @admin.action(description="Mark selected orders as paid")
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(
            status=Order.Status.PAID,
            paid_at=timezone.now(),
        )

        self.message_user(
            request,
            f"{updated} orders marked as paid.",
            messages.SUCCESS,
        )

    @admin.action(description="Mark selected orders as shipped")
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(
            shipping_status=Order.ShippingStatus.SHIPPED,
            shipped_at=timezone.now(),
        )

        self.message_user(
            request,
            f"{updated} orders marked as shipped.",
            messages.SUCCESS,
        )
    

@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):

    autocomplete_fields = (
        "order",
        "variant",
    )

    list_select_related = (
        "order",
        "variant",
    )

    search_fields = (
        "order__order_number",
        "variant__sku",
    )

    list_display = (
        "order",
        "variant",
        "quantity",
        "unit_price",
        "total_price",
    )

    readonly_fields = (
        "total_price",
    )
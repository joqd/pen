from django.contrib import admin
from django.contrib.admin import display
from django.db.models import Count, F, Sum
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline

from apps.orders.models import Cart, CartItem


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
                total_sum=Sum(F('items__quantity') * F('items__variant__price')),
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

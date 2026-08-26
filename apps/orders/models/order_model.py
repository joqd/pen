from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Address
from apps.catalog.models import ProductVariant

from .cart_model import Cart

User = get_user_model()


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', _('pending payment')
        PROCESSING = 'processing', _('processing')
        PAID = 'paid', _('paid')
        CANCELLED = 'cancelled', _('cancelled')
        EXPIRED = 'expired', _('expired')
        REFUNDED = 'refunded', _('refunded')

    class ShippingStatus(models.TextChoices):
        PENDING = 'pending', _('pending')
        PROCESSING = 'processing', _('processing')
        SHIPPED = 'shipped', _('shipped')
        DELIVERED = 'delivered', _('delivered')
        RETURNED = 'returned', _('returned')

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders', verbose_name=_('user'))
    address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='orders', verbose_name=_('address'))
    # Traceability back to the cart this order was created from. SET_NULL
    # (not CASCADE) so deleting/clearing an old cart never touches the order.
    cart = models.ForeignKey(
        Cart, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name=_('cart')
    )
    order_number = models.CharField(_('order number'), max_length=32, unique=True, editable=False)

    # Public identifier used in payment callback URLs / frontend routes so we
    # never leak the internal pk and can't be guessed/enumerated.
    token = models.UUIDField(_('token'), default=uuid4, unique=True, editable=False, db_index=True)

    status = models.CharField(_('status'), max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT)
    shipping_status = models.CharField(
        _('shipping status'), max_length=30, choices=ShippingStatus.choices, default=ShippingStatus.PENDING
    )

    subtotal_amount = models.PositiveIntegerField(_('subtotal amount'), default=0)
    shipping_amount = models.PositiveIntegerField(_('shipping amount'), default=0)
    discount_amount = models.PositiveIntegerField(_('discount amount'), default=0)
    total_amount = models.PositiveIntegerField(_('total amount'), default=0)

    tracking_code = models.CharField(_('tracking code'), max_length=100, blank=True)
    shipping_company = models.CharField(_('shipping company'), max_length=100, blank=True)
    customer_note = models.TextField(_('customer note'), blank=True)
    admin_note = models.TextField(_('admin note'), blank=True)

    expires_at = models.DateTimeField(_('expires at'))
    paid_at = models.DateTimeField(_('paid at'), null=True, blank=True)
    shipped_at = models.DateTimeField(_('shipped at'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('delivered at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')
        ordering = ['-id']
        indexes = [
            # used heavily by the expiry sweep task
            models.Index(fields=['status', 'expires_at']),
            # used by "my orders" / order history queries
            models.Index(fields=['user', 'status']),
        ]
        constraints = [
            # Optional but recommended: keeps totals honest at the DB layer,
            # not just in application code. Drop this if you later add
            # taxes/fees that break the simple subtotal+shipping-discount
            # formula, or if you're on MySQL < 8.0.16 (CHECK is a no-op there).
            models.CheckConstraint(
                condition=models.Q(
                    total_amount=models.F('subtotal_amount') + models.F('shipping_amount') - models.F('discount_amount')
                ),
                name='order_total_amount_consistent',
            ),
        ]

    def __str__(self):
        return self.order_number

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.order_number:
            self.order_number = str(100000 + self.pk)
            super().save(update_fields=['order_number'])

    @property
    def is_expired(self) -> bool:
        return self.status == self.Status.PENDING_PAYMENT and self.expires_at <= timezone.now()

    @property
    def is_payable(self) -> bool:
        return self.status == self.Status.PENDING_PAYMENT and not self.is_expired


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name=_('order'))
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='+', verbose_name=_('variant'))

    # Snapshot fields. The catalog (title, sku, options) can be edited or
    # retranslated after the sale — an order must keep showing exactly what
    # the buyer purchased, regardless of later catalog changes.
    title = models.CharField(_('title'), max_length=255)
    sku = models.CharField(_('sku'), max_length=64)
    options = models.JSONField(_('options'), default=dict, blank=True)

    quantity = models.PositiveIntegerField(_('quantity'), default=1)
    unit_price = models.PositiveIntegerField(_('unit price'))
    total_price = models.PositiveIntegerField(_('total price'))

    class Meta:
        verbose_name = _('order item')
        verbose_name_plural = _('order items')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='order_item_quantity_gte_1',
            ),
            models.CheckConstraint(
                condition=models.Q(total_price=models.F('unit_price') * models.F('quantity')),
                name='order_item_total_price_consistent',
            ),
        ]

    def __str__(self):
        return f'{self.title} ({self.sku}) x{self.quantity}'
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Address
from apps.catalog.models import ProductVariant

User = get_user_model()


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', _('pending payment')
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
    address = models.ForeignKey(Address, on_delete=models.PROTECT, verbose_name=_('address'))
    order_number = models.CharField(_('order number'), max_length=32, unique=True)

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

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.order_number:
            self.order_number = str(100000 + self.pk)
            super().save(update_fields=['order_number'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name=_('order'))
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, verbose_name=_('variant'))

    quantity = models.PositiveIntegerField(_('quantity'), default=1)
    unit_price = models.PositiveIntegerField(_('price'))
    total_price = models.PositiveIntegerField(_('total price'))

    class Meta:
        verbose_name = _('order item')
        verbose_name_plural = _('order items')

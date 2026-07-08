from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ProductVariant, Product

from uuid import uuid4

User = get_user_model()


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True, verbose_name=_('user'))
    token = models.UUIDField(_('token'), default=uuid4, unique=True, editable=False, db_index=True)
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('cart')
        verbose_name_plural = _('carts')

    @property
    def is_guest(self):
        return self.user_id is None
    
    def __str__(self):
        return str(self.user.phone) if self.user else 'کاربر میهمان'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name=_('cart'))
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='+', verbose_name=_('product'))
    quantity = models.PositiveIntegerField(_('quantity'), default=1)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('cart item')
        verbose_name_plural = _('cart items')
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'variant'],
                name='unique_variant_in_cart',
            )
        ]

    def __str__(self):
        return f'{self.variant.product.title} - {self.variant.sku}'
    

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items', verbose_name=_('user'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_('product'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('wishlist item'),
        verbose_name_plural = _('wishlist items')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_product_wishlist',
            )
        ]
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'created_at']),
        ]
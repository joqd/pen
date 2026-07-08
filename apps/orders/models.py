from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ProductVariant

from uuid import uuid4

User = get_user_model()


class Cart(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True, verbose_name=_('user'))
	token = models.UUIDField(_('token'), default=uuid4, unique=True, editable=False, db_index=True)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = _('cart')
		verbose_name_plural = _('carts')

	@property
	def is_guest(self):
		return self.user_id is None


class CartItem(models.Model):
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name=_('cart'))
	variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='+', verbose_name=_('product'))
	quantity = models.PositiveIntegerField(default=1)

	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = _('Cart Item')
		verbose_name_plural = _('Cart Items')
		constraints = [
			models.UniqueConstraint(
				fields=['cart', 'variant'],
				name='unique_variant_in_cart',
			)
		]
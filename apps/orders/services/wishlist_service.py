from django.core.exceptions import ValidationError

from ..models import WishlistItem


class WishlistService:
    MAX_ITEMS = 50

    @classmethod
    def add_item(cls, user, product):
        exists = WishlistItem.objects.filter(user=user, product=product).exists()
        if exists:
            return

        count = WishlistItem.objects.filter(user=user).count()
        if count >= cls.MAX_ITEMS:
            raise ValidationError('Wishlist item limit reached.')

        WishlistItem.objects.create(user=user, product=product)

    @classmethod
    def remove_item(cls, user, product):
        WishlistItem.objects.filter(user=user, product=product).delete()

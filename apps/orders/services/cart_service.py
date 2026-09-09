from django.db import transaction
from rest_framework.exceptions import ValidationError

from ..models import Cart, CartItem


class CartService:
    MAX_CART_ITEMS = 100
    MAX_ITEM_QUANTITY = 20

    @classmethod
    def get_or_create_cart(cls, user=None, token=None):
        if user and user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=user)
            return cart

        if token:
            cart = Cart.objects.filter(
                token=token,
                user__isnull=True,
            ).first()

            if cart:
                return cart

        return Cart.objects.create()

    @classmethod
    def add_item(cls, cart, variant, quantity):
        if quantity > cls.MAX_ITEM_QUANTITY:
            raise ValidationError(f'Maximum quantity is {cls.MAX_ITEM_QUANTITY}.')

        # Must compare against available_stock (stock - reserved_stock), not
        # raw stock. Raw stock ignores units already reserved by *other*
        # customers' pending orders, so validating against it here would let
        # a cart hold a quantity that create_order_from_cart's (correct)
        # available_stock check then rejects at checkout time - i.e. the
        # exact "insufficient stock" error we're trying to avoid, on a
        # product that still looks available.
        if quantity > variant.available_stock:
            raise ValidationError('Insufficient stock.')

        item = CartItem.objects.filter(
            cart=cart,
            variant=variant,
        ).first()

        if item:
            requested = item.quantity + quantity

            if requested > cls.MAX_ITEM_QUANTITY:
                raise ValidationError(f'Maximum quantity is {cls.MAX_ITEM_QUANTITY}.')

            if requested > variant.available_stock:
                raise ValidationError('Insufficient stock.')

            item.quantity = requested
            item.save(update_fields=['quantity'])

            return item

        cart_items_count = cart.items.count()

        if cart_items_count >= cls.MAX_CART_ITEMS:
            raise ValidationError('Cart item limit reached.')

        return CartItem.objects.create(
            cart=cart,
            variant=variant,
            quantity=quantity,
        )

    @classmethod
    def update_quantity(cls, item, quantity):

        if quantity > cls.MAX_ITEM_QUANTITY:
            raise ValidationError(f'Maximum quantity is {cls.MAX_ITEM_QUANTITY}.')

        if quantity > item.variant.available_stock:
            raise ValidationError('Insufficient stock.')

        item.quantity = quantity
        item.save(update_fields=['quantity'])

    @classmethod
    def remove_item(cls, item):
        item.delete()

    @classmethod
    @transaction.atomic
    def merge_guest_cart(cls, guest_cart, user):
        user_cart, _ = Cart.objects.get_or_create(user=user)

        for guest_item in guest_cart.items.all():
            existing = user_cart.items.filter(variant_id=guest_item.variant_id).first()

            if existing:
                new_quantity = min(existing.variant.available_stock, existing.quantity + guest_item.quantity)

                existing.quantity = new_quantity
                existing.save(update_fields=['quantity'])
            else:
                guest_item.quantity = min(guest_item.quantity, guest_item.variant.available_stock)
                guest_item.cart = user_cart
                guest_item.save(update_fields=['quantity', 'cart'])

        guest_cart.delete()
        return user_cart

    @classmethod
    @transaction.atomic
    def merge_cart_from_token(cls, *, user, token):
        if not token:
            return

        guest_cart = Cart.objects.filter(
            token=token,
            user__isnull=True,
        ).first()

        if not guest_cart:
            return

        cls.merge_guest_cart(
            guest_cart=guest_cart,
            user=user,
        )

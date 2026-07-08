from django.db import transaction
from rest_framework.exceptions import ValidationError

from ..models import CartItem, Cart

class CartService:
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
        if quantity > variant.stock:
            raise ValidationError('Insufficient stock')
        
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={
                'quantity': quantity
            }
        )

        if not created:
            requested = item.quantity + quantity
            if requested > variant.stock:
                raise ValidationError('Insufficient stock')
            
            item.quantity = requested
            item.save(
                update_fields=['quantity']
            )

        return item


    @classmethod
    def update_quantity(cls, item, quantity):
        if quantity > item.variant.stock:
            raise ValidationError('Insufficient stock')
        
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

            existing = user_cart.items.filter(
                variant_id=guest_item.variant_id
            ).first()

            if existing:
                new_quantity = min(
                    existing.variant.stock,
                    existing.quantity + guest_item.quantity
                )

                existing.quantity = new_quantity
                existing.save(update_fields=['quantity'])
            else:
                guest_item.quantity = min(guest_item.quantity, guest_item.variant.stock)
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
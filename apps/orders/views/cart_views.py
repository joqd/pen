from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..serializers.cart_serializers import (
    CartSerializer,
    AddCartItemSerializer,
    UpdateCartItemSerializer,
)
from ..services.cart_service import CartService
from apps.catalog.models import ProductVariant
from ..models import CartItem
from .mixins import CartMixin


class CartView(CartMixin, APIView):
    def get(self, request):
        cart = self.get_cart(request)
        serializer = CartSerializer(cart)

        response = Response(serializer.data)
        if not request.user.is_authenticated and not request.COOKIES.get('cart_token'):
            response.set_cookie(
                key='cart_token',
                value=str(cart.token),
                max_age=60 * 60 * 24 * 30,  # 30 days
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax',
            )

        return response
    

class CartItemCreateView(CartMixin, APIView):
    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_cart(request)
        variant = get_object_or_404(
            ProductVariant.objects.filter(is_active=True),
            pk=serializer.validated_data['variant_id']
        )

        CartService.add_item(cart=cart, variant=variant, quantity=serializer.validated_data['quantity'])

        return Response(status=status.HTTP_201_CREATED)
    

class CartItemUpdateView(CartMixin, APIView):
    def patch(self, request, item_id):
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_cart(request)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)

        CartService.update_quantity(
            item=item,
            quantity=serializer.validated_data['quantity']
        )

        return Response(status=status.HTTP_200_OK)


class CartItemDeleteView(CartMixin, APIView):
    def delete(self, request, item_id):
        cart = self.get_cart(request)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)

        CartService.remove_item(item)

        return Response(status=status.HTTP_204_NO_CONTENT)
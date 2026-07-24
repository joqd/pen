from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ProductVariant

from ..models import CartItem
from ..serializers.cart_serializer import (
    AddCartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)
from ..services.cart_service import CartService
from .mixins import CartMixin


class CartView(CartMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Carts'],
        summary='Get current cart',
        description=(
            'Returns current cart for guest or authenticated user. '
            'For guest users, a cart_token cookie will be created automatically.'
        ),
        responses={
            200: CartSerializer,
        },
    )
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
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Carts'],
        summary='Add item to cart',
        description=(
            'Adds a product variant to the current cart. '
            'The item is identified by SKU. '
            'If the variant already exists in the cart, quantity will be increased.'
        ),
        request=AddCartItemSerializer,
        responses={
            201: OpenApiResponse(
                response=CartSerializer,
                description='Cart updated successfully.',
            ),
            400: OpenApiResponse(description='Invalid quantity or insufficient stock.'),
            404: OpenApiResponse(description='Product variant not found.'),
        },
    )
    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_cart(request)
        variant = get_object_or_404(
            ProductVariant.objects.filter(is_active=True),
            sku=serializer.validated_data['sku'],
        )

        CartService.add_item(cart=cart, variant=variant, quantity=serializer.validated_data['quantity'])

        cart.refresh_from_db()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CartItemView(CartMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Carts'],
        summary='Update cart item quantity',
        description=('Updates quantity of an existing cart item. SKU is used to identify the product variant.'),
        parameters=[
            OpenApiParameter(
                name='sku',
                type=str,
                location=OpenApiParameter.PATH,
                description='Product variant SKU',
            )
        ],
        request=UpdateCartItemSerializer,
        responses={
            200: OpenApiResponse(
                response=CartSerializer,
                description='Cart updated successfully.',
            ),
            404: OpenApiResponse(description='Cart item not found.'),
        },
    )
    def patch(self, request, sku):
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_cart(request)
        item = get_object_or_404(CartItem, variant__sku=sku, cart=cart)

        CartService.update_quantity(item=item, quantity=serializer.validated_data['quantity'])

        cart.refresh_from_db()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Carts'],
        summary='Remove item from cart',
        description=('Removes a product variant completely from the current cart.'),
        parameters=[
            OpenApiParameter(
                name='sku',
                type=str,
                location=OpenApiParameter.PATH,
                description='Product variant SKU',
            )
        ],
        responses={
            200: OpenApiResponse(
                response=CartSerializer,
                description='Cart updated successfully.',
            ),
            404: OpenApiResponse(description='Cart item not found.'),
        },
    )
    def delete(self, request, sku):
        cart = self.get_cart(request)
        item = get_object_or_404(CartItem, variant__sku=sku, cart=cart)

        CartService.remove_item(item)

        cart.refresh_from_db()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

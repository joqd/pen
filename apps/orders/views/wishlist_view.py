from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
)

from apps.catalog.models import Product
from apps.orders.models import WishlistItem
from apps.orders.services.wishlist_service import WishlistService
from apps.orders.serializers.wishlist_serializer import (
    WishlistItemSerializer,
    AddWishlistItemSerializer,
)


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Wishlist'],
        summary='Get wishlist',
        description=(
            'Returns all products saved in the authenticated '
            'user wishlist.'
        ),
        responses={
            200: WishlistItemSerializer(many=True),
        },
    )
    def get(self, request):
        items = (
            WishlistItem.objects
            .filter(user=request.user)
            .select_related('product')
            .order_by('-created_at')
        )

        serializer = WishlistItemSerializer(items, many=True)
        return Response(serializer.data)
    

class WishlistItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Wishlist'],
        summary='Add product to wishlist',
        description=(
            'Adds a product to the authenticated user wishlist. '
            'If the product already exists in wishlist, '
            'nothing happens.'
        ),
        request=AddWishlistItemSerializer,
        responses={
            201: OpenApiResponse(
                response=WishlistItemSerializer(many=True),
                description='Wishlist updated successfully.',
            ),
            400: OpenApiResponse(
                description='Wishlist limit reached.',
            ),
            404: OpenApiResponse(
                description='Product not found.',
            ),
        },
    )
    def post(self, request):
        serializer = AddWishlistItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = get_object_or_404(
            Product,
            slug=serializer.validated_data['slug'],
        )

        WishlistService.add_item(user=request.user, product=product)

        items = (
            request.user
            .wishlist_items
            .select_related('product')
            .order_by('-created_at')
        )

        return Response(
            WishlistItemSerializer(
                items,
                many=True,
            ).data,
            status=status.HTTP_201_CREATED,
        )
    

class WishlistItemView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Wishlist'],
        summary='Remove product from wishlist',
        description=(
            'Removes a product from the authenticated '
            'user wishlist.'
        ),
        parameters=[
            OpenApiParameter(
                name='slug',
                type=str,
                location=OpenApiParameter.PATH,
                description='Product slug',
            )
        ],
        responses={
            200: OpenApiResponse(
                response=WishlistItemSerializer(many=True),
                description='Wishlist updated successfully.',
            ),
            404: OpenApiResponse(
                description='Product not found.',
            ),
        },
    )
    def delete(self, request, slug):
        product = get_object_or_404(Product, slug=slug)

        WishlistService.remove_item(
            user=request.user,
            product=product,
        )

        items = (
            request.user
            .wishlist_items
            .select_related("product")
            .order_by("-created_at")
        )

        return Response(
            WishlistItemSerializer(
                items,
                many=True,
            ).data,
            status=status.HTTP_200_OK,
        )
from django.db.models import Q
from django_filters import rest_framework as django_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Product
from ..serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
)
from ..models import Review, ReviewStatus
from ..serializers import ReviewReadSerializer


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class ProductFilter(django_filters.FilterSet):
    collections = CharInFilter(field_name='collections__slug', lookup_expr='in', label='Collection slugs')
    category = django_filters.CharFilter(field_name='category__slug', label='Category slug')
    featured = django_filters.BooleanFilter(label='Featured products')

    class Meta:
        model = Product
        fields = ['featured', 'collections', 'category']


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]

    queryset = Product.objects.filter(status='active')
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['title', 'slug', 'short_description']
    ordering_fields = ['created_at', 'published_at', 'title']
    ordering = ['-published_at', '-id']
    lookup_field = 'slug'
    tags = ['Products']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'images',
                'variants__size',
                'collections',
                'tags',
            )
        elif self.action == 'list':
            queryset = queryset.prefetch_related('collections', 'images')

        if 'collections' in self.request.query_params:
            queryset = queryset.distinct()

        return queryset

    @extend_schema(tags=['Products'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=['Products'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=['Products'], responses=ReviewReadSerializer(many=True))
    @action(detail=True, methods=['get'], url_path='reviews', pagination_class=StandardPagination)
    def reviews(self, request, slug=None):
        product = self.get_object()

        qs = Review.objects.filter(product=product).select_related('user', 'product')

        user = request.user
        if user.is_authenticated and user.is_staff:
            pass
        elif user.is_authenticated:
            qs = qs.filter(Q(status=ReviewStatus.APPROVED) | Q(user=user))
        else:
            qs = qs.filter(status=ReviewStatus.APPROVED)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ReviewReadSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ReviewReadSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)
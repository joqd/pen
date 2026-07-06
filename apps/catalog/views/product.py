from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from ..models import Product
from ..serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for reading Product objects."""
    queryset = Product.objects.filter(status='active')
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {'featured': ['exact'], 'collections__slug': ['exact']}
    search_fields = ['title', 'slug', 'short_description']
    ordering_fields = ['created_at', 'published_at', 'title']
    ordering = ['-published_at', '-id']
    lookup_field = 'slug'
    tags = ['Products']

    def get_serializer_class(self):
        """Return list or detail serializer based on action."""
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        """Optimize queryset with select_related and prefetch_related."""
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
        return queryset

    @extend_schema(tags=['Products'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=['Products'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


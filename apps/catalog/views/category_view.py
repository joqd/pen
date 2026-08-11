from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination

from ..models import Category
from ..serializers import CategoryDetailSerializer, CategoryListSerializer


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]

    queryset = Category.objects.filter(is_active=True)
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'slug', 'short_description']
    ordering_fields = ['title', 'created_at']
    ordering = ['title']
    lookup_field = 'slug'
    tags = ['Categories']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategoryListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('children', 'products').select_related('parent')
        return queryset

    @extend_schema(tags=['Categories'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=['Categories'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

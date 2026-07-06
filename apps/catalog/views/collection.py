from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema

from ..models import Collection
from ..serializers import (
    CollectionListSerializer,
    CollectionDetailSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for reading Collection objects."""
    queryset = Collection.objects.filter(is_active=True)
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'slug', 'short_description']
    ordering_fields = ['title', 'created_at']
    ordering = ['title']
    lookup_field = 'slug'
    tags = ['Collections']

    def get_serializer_class(self):
        """Return list or detail serializer based on action."""
        if self.action == 'retrieve':
            return CollectionDetailSerializer
        return CollectionListSerializer

    def get_queryset(self):
        """Optimize queryset with prefetch_related."""
        queryset = super().get_queryset()
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('children')
        return queryset
    
    @extend_schema(tags=['Collection'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=['Collection'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


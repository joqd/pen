from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from ..models import CustomerGallery
from ..serializers import CustomerGallerySerializer


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(tags=['Gallery'])
class CustomerGalleryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CustomerGallerySerializer
    pagination_class = StandardPagination

    queryset = CustomerGallery.objects.filter(is_active=True).select_related('product').order_by('sort_order', '-id')

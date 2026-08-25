from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema

from ..models import FooterBadge
from ..serializers.site_serializer import FooterBadgeSerializer


@extend_schema(tags=['Site Settings'])
class FooterBadgeListView(ListAPIView):
    serializer_class = FooterBadgeSerializer
    permission_classes = []

    def get_queryset(self):
        return FooterBadge.objects.filter(is_active=True)

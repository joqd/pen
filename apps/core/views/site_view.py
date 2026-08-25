from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema

from ..models import FooterBadge, PaymentGateway
from ..serializers.site_serializer import FooterBadgeSerializer, PaymentGatewaySerializer


@extend_schema(tags=['Site Settings'])
class FooterBadgeListView(ListAPIView):
    serializer_class = FooterBadgeSerializer
    permission_classes = []

    def get_queryset(self):
        return FooterBadge.objects.filter(is_active=True)


@extend_schema(tags=['Site Settings'])
class PaymentGatewayListView(ListAPIView):
    serializer_class = PaymentGatewaySerializer
    permission_classes = []

    def get_queryset(self):
        return PaymentGateway.objects.filter(is_active=True)

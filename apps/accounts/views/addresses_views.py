from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema

from ..models import Address
from ..serializers import AddressSerializer


@extend_schema(tags=['Addresses'])
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Address.objects
            .filter(user=self.request.user)
            .select_related(
                'province',
                'city',
            )
            .order_by(
                '-is_default',
                '-id',
            )
        )

    def perform_create(self, serializer):
        address = serializer.save(user=self.request.user)

        if address.is_default:
            Address.objects.filter(
                user=self.request.user,
            ).exclude(
                pk=address.pk,
            ).update(
                is_default=False,
            )

    def perform_update(self, serializer):
        address = serializer.save()

        if address.is_default:
            Address.objects.filter(
                user=self.request.user,
            ).exclude(
                pk=address.pk,
            ).update(
                is_default=False,
            )
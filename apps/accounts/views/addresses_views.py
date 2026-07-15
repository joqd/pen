from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView, ListAPIView

from drf_spectacular.utils import extend_schema

from ..models import Address, Province, City
from ..serializers import AddressSerializer, ProvinceSerializer, CitySerializer
from ..serializers import AddressWriteSerializer


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
            
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AddressWriteSerializer

        return AddressSerializer
            

@extend_schema(tags=['Province and City'])
class ProvinceListAPIView(ListAPIView):
    queryset = Province.objects.all()
    serializer_class = ProvinceSerializer


@extend_schema(tags=['Province and City'])
class ProvinceCityListAPIView(ListAPIView):
    serializer_class = CitySerializer

    def get_queryset(self):
        province_id = self.kwargs['province_id']

        return (
            City.objects
            .select_related('province')
            .filter(province_id=province_id)
        )


@extend_schema(tags=['Province and City'])
class CityListAPIView(ListAPIView):
    queryset = City.objects.select_related('province')
    serializer_class = CitySerializer
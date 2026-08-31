from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from ..models import Address, City, Province
from ..serializers import AddressSerializer, AddressWriteSerializer, CitySerializer, ProvinceSerializer


@extend_schema(tags=['Addresses'])
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Address.objects.filter(user=self.request.user)
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


@extend_schema(tags=['Provinces and Cities'])
class ProvinceListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    queryset = Province.objects.all()
    serializer_class = ProvinceSerializer
    pagination_class = None


@extend_schema(tags=['Provinces and Cities'])
class ProvinceCityListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CitySerializer
    pagination_class = None

    def get_queryset(self):
        province_id = self.kwargs['province_id']

        return City.objects.select_related('province').filter(
            province_id=province_id
        )


@extend_schema(tags=['Provinces and Cities'])
class CityListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    queryset = City.objects.select_related('province')
    serializer_class = CitySerializer

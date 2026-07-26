from rest_framework import serializers

from ..models import Address, City, Province


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ('id', 'name')


class CitySerializer(serializers.ModelSerializer):
    province_id = serializers.IntegerField(source='province.id', read_only=True)

    class Meta:
        model = City
        fields = ('id', 'name', 'province_id')


class AddressSerializer(serializers.ModelSerializer):
    province = ProvinceSerializer()
    city = CitySerializer()

    class Meta:
        model = Address
        fields = [
            'id',
            'title',
            'recipient_name',
            'phone',
            'province',
            'city',
            'postal_code',
            'address_line',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AddressWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'title',
            'recipient_name',
            'phone',
            'province',
            'city',
            'postal_code',
            'address_line',
            'is_default',
        ]

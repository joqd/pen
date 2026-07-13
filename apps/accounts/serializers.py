from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Address, Province, City

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=13)


class LoginResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True, required=False)


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class UserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    phone = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)


class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)


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
            'id', 'title', 'recipient_name',
            'phone', 'province', 'city',
            'postal_code', 'address_line',
            'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        province = attrs.get(
            'province',
            getattr(self.instance, 'province', None),
        )

        city = attrs.get(
            'city',
            getattr(self.instance, 'city', None),
        )

        if city and province and city.province_id != province.id:
            raise serializers.ValidationError({
                'city': 'Selected city does not belong to selected province.'
            })

        return attrs
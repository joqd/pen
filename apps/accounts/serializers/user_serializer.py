from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=14)


class LoginResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)
    code = serializers.CharField(max_length=6, read_only=True, required=False)


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name', 'avatar']


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=14)
    code = serializers.CharField(max_length=6)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'full_name',
            'avatar',
        ]

    def validate_full_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(_('name must be at least 2 characters.'))

        return value

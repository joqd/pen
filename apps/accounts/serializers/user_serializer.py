from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=13)


class LoginResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True, required=False)


class UserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    phone = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)

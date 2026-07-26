from rest_framework import serializers


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)

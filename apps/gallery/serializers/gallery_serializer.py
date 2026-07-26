from rest_framework import serializers

from ..models import CustomerGallery


class CustomerGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGallery
        fields = [
            'id',
            'image',
            'customer_name',
            'caption',
            'score',
            'created_at',
        ]

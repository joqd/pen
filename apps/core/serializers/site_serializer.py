from rest_framework import serializers

from ..models import FooterBadge, PaymentGateway


class FooterBadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FooterBadge
        fields = [
            'id',
            'title',
            'html',
            'priority',
        ]


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = [
            'id',
            'title',
            'badge',
            'priority',
        ]

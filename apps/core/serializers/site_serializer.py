from rest_framework import serializers

from ..models import FooterBadge


class FooterBadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FooterBadge
        fields = [
            'id',
            'title',
            'html',
            'priority',
        ]

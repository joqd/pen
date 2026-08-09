from rest_framework import serializers

from ..models.metatag_model import MetaTag


class MetaTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaTag
        fields = [
            'title',
            'description',
            'canonical_url',
            'is_indexable',
            'og_title',
            'og_description',
            'og_image',
            'twitter_card',
        ]

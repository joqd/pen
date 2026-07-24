from rest_framework import serializers

from ..models import Collection


class CollectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'title', 'slug', 'short_description', 'image', 'is_active', 'parent']
        read_only_fields = fields


class CollectionDetailSerializer(serializers.ModelSerializer):
    children = CollectionListSerializer(many=True, read_only=True)
    parent_detail = CollectionListSerializer(source='parent', read_only=True)

    class Meta:
        model = Collection
        fields = [
            'id',
            'title',
            'slug',
            'parent',
            'parent_detail',
            'short_description',
            'description',
            'is_active',
            'image',
            'children',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


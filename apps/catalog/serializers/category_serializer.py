from rest_framework import serializers

from apps.seo.serializers import MetaTagSerializer

from ..models import Category
from .product_serializer import ProductListSerializer


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug', 'short_description', 'image', 'is_active', 'parent']
        read_only_fields = fields


class CategoryDetailSerializer(serializers.ModelSerializer):
    children = CategoryListSerializer(many=True, read_only=True)
    parent_detail = CategoryListSerializer(source='parent', read_only=True)
    products = ProductListSerializer(many=True, read_only=True)
    meta_tag = MetaTagSerializer(read_only=True)

    class Meta:
        model = Category
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
            'products',
            'meta_tag',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

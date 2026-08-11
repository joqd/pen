from rest_framework import serializers

from apps.seo.serializers.metatag_serializer import MetaTagSerializer
from apps.seo.views.schema_builders_view import BreadcrumbSchemaBuilder, CategorySchemaBuilder

from ..models import Category
from .product_serializer import ProductListSerializer


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug', 'short_description', 'image', 'image_dark', 'is_active', 'parent']
        read_only_fields = fields


class CategoryDetailSerializer(serializers.ModelSerializer):
    children = CategoryListSerializer(many=True, read_only=True)
    parent_detail = CategoryListSerializer(source='parent', read_only=True)
    products = ProductListSerializer(many=True, read_only=True)
    meta_tag = MetaTagSerializer(read_only=True)
    json_ld = serializers.SerializerMethodField()
    breadcrumb_ld = serializers.SerializerMethodField()

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
            'image_dark',
            'children',
            'products',
            'meta_tag',
            'json_ld',
            'breadcrumb_ld',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_json_ld(self, obj) -> dict:
        return CategorySchemaBuilder(obj, request=self.context.get('request')).to_json_ld()

    def get_breadcrumb_ld(self, obj) -> dict:
        return BreadcrumbSchemaBuilder.for_category(obj, request=self.context.get('request')).to_json_ld()

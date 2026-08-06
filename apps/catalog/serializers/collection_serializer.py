from rest_framework import serializers

from apps.seo.serializers import MetaTagSerializer

from apps.seo.schema_builders import CollectionSchemaBuilder, BreadcrumbSchemaBuilder
from ..models import Collection


class CollectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'title', 'slug', 'short_description', 'image', 'is_active', 'parent']
        read_only_fields = fields


class CollectionDetailSerializer(serializers.ModelSerializer):
    children = CollectionListSerializer(many=True, read_only=True)
    parent_detail = CollectionListSerializer(source='parent', read_only=True)
    meta_tag = MetaTagSerializer(read_only=True)
    json_ld = serializers.SerializerMethodField()
    breadcrumb_ld = serializers.SerializerMethodField()

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
            'meta_tag',
            'json_ld',
            'breadcrumb_ld',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_json_ld(self, obj) -> dict:
        return CollectionSchemaBuilder(obj, request=self.context.get("request")).to_json_ld()

    def get_breadcrumb_ld(self, obj) -> dict:
        return BreadcrumbSchemaBuilder.for_category(obj, request=self.context.get("request")).to_json_ld()

from rest_framework import serializers

from apps.seo.schema_builders import BreadcrumbSchemaBuilder, ProductSchemaBuilder
from apps.seo.serializers import MetaTagSerializer

from ..models import Product, ProductImage, ProductVariant, ProductSize, SizeAttribute
from .audio_serializer import AudioSerializer
from .collection_serializer import CollectionListSerializer


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'media_kind', 'caption', 'alt_text', 'is_primary']
        read_only_fields = fields



class SizeAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeAttribute
        fields = ['key', 'value', 'sort_order']
    

class ProductSizeSerializer(serializers.ModelSerializer):
    attributes = SizeAttributeSerializer(many=True)

    class Meta:
        model = ProductSize
        fields = ['name', 'label', 'attributes']


class ProductVariantSerializer(serializers.ModelSerializer):
    size_name = serializers.CharField(source='size.name', read_only=True)
    size = ProductSizeSerializer(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'sku', 'size', 'size_name', 'price', 'compare_price', 'stock', 'is_active']
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    collections_list = serializers.StringRelatedField(source='collections', many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'slug',
            'short_description',
            'featured',
            'published_at',
            'images',
            'variants',
            'collections_list',
        ]
        read_only_fields = fields


class ProductDetailSerializer(serializers.ModelSerializer):
    collections = CollectionListSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    audio = serializers.SerializerMethodField()
    variants = ProductVariantSerializer(many=True, read_only=True)
    is_in_wishlist = serializers.SerializerMethodField()
    meta_tag = MetaTagSerializer(read_only=True)
    json_ld = serializers.SerializerMethodField()
    breadcrumb_ld = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'slug',
            'short_description',
            'description',
            'status',
            'published_at',
            'featured',
            'collections',
            'images',
            'audio',
            'variants',
            'is_in_wishlist',
            'meta_tag',
            'json_ld',
            'breadcrumb_ld',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_is_in_wishlist(self, obj):
        request = self.context.get('request')

        if not request or not request.user.is_authenticated:
            return False

        return request.user.wishlist_items.filter(product_id=obj.id).exists()

    def get_audio(self, obj):
        if not hasattr(obj, 'audio'):
            return None

        return AudioSerializer(
            obj.audio,
            context=self.context,
        ).data

    def get_json_ld(self, obj) -> dict:
        request = self.context.get('request')
        return ProductSchemaBuilder(obj, request=request).to_json_ld()

    def get_breadcrumb_ld(self, obj) -> dict:
        request = self.context.get('request')
        return BreadcrumbSchemaBuilder.for_product(obj, request=request).to_json_ld()

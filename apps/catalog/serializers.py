from rest_framework import serializers
from .models import Product, Collection, ProductImage, ProductVariant, Tag, ProductSize


# Collection Serializers
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


# Product Serializers
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'media_kind', 'caption', 'alt_text', 'is_primary']
        read_only_fields = fields


class ProductVariantSerializer(serializers.ModelSerializer):
    size_name = serializers.CharField(source='size.name', read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = ['id', 'sku', 'size', 'size_name', 'price', 'compare_price', 'stock', 'is_active']
        read_only_fields = fields


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'title', 'slug']
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
            'status',
            'featured',
            'published_at',
            'images',
            'variants',
            'collections_list',
        ]
        read_only_fields = fields


class ProductDetailSerializer(serializers.ModelSerializer):
    collections = CollectionListSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    is_in_wishlist = serializers.SerializerMethodField()
    
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
            'tags',
            'images',
            'variants',
            'is_in_wishlist',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_is_in_wishlist(self, obj):
        request = self.context.get('request')

        if not request or not request.user.is_authenticated:
            return False

        return request.user.wishlist_items.filter(
            product_id=obj.id
        ).exists()
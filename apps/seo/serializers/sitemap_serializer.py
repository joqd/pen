from rest_framework import serializers

from apps.blog.models.post_model import Post
from apps.catalog.models.category_model import Category
from apps.catalog.models.collection_model import Collection
from apps.catalog.models.product_model import Product


class PostSitemapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('slug', 'updated_at')


class ProductSitemapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('slug', 'updated_at')


class CollectionSitemapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ('slug', 'updated_at')


class CategorySitemapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('slug', 'updated_at')

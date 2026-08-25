from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from apps.blog.models.post_model import Post
from apps.catalog.models.category_model import Category
from apps.catalog.models.collection_model import Collection
from apps.catalog.models.product_model import Product, ProductStatus


class SitemapItemSerializer(serializers.Serializer):
    slug = serializers.CharField()
    updated_at = serializers.DateTimeField()


class BaseSitemapView(ListAPIView):
    """
    Base view for sitemap endpoints.
    No pagination — item counts are expected to stay small (< 100).
    """

    permission_classes = [AllowAny]
    serializer_class = SitemapItemSerializer
    pagination_class = None


class PostSitemapView(BaseSitemapView):
    @extend_schema(
        summary='Get post sitemap items',
        description='Returns slug and last updated timestamp for all published posts.',
        tags=['Sitemap'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Post.objects.filter(status=Post.Status.PUBLISHED).only('slug', 'updated_at')


class ProductSitemapView(BaseSitemapView):
    @extend_schema(
        summary='Get product sitemap items',
        description='Returns slug and last updated timestamp for all active products.',
        tags=['Sitemap'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Product.objects.filter(status=ProductStatus.ACTIVE).only('slug', 'updated_at')


class CollectionSitemapView(BaseSitemapView):
    @extend_schema(
        summary='Get collection sitemap items',
        description='Returns slug and last updated timestamp for all active collections.',
        tags=['Sitemap'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Collection.objects.filter(is_active=True).only('slug', 'updated_at')


class CategorySitemapView(BaseSitemapView):
    @extend_schema(
        summary='Get category sitemap items',
        description='Returns slug and last updated timestamp for all active categories.',
        tags=['Sitemap'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Category.objects.filter(is_active=True).only('slug', 'updated_at')

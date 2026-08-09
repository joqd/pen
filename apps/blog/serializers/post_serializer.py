from rest_framework import serializers

from apps.seo.serializers.metatag_serializer import MetaTagSerializer
from apps.seo.views.schema_builders_view import ArticleSchemaBuilder, BreadcrumbSchemaBuilder

from ..models.post_model import Post, PostMedia


class PostMediaSerializer(serializers.ModelSerializer):
    is_video = serializers.ReadOnlyField()

    class Meta:
        model = PostMedia
        fields = (
            'id',
            'file',
            'alt_text',
            'is_video',
        )


class PostListSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    author = serializers.StringRelatedField()
    featured_image = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            'id',
            'title',
            'slug',
            'excerpt',
            'featured',
            'featured_image',
            'category',
            'author',
            'published_at',
            'view_count',
        )

    def get_featured_image(self, obj):
        if not obj.featured_image:
            return None

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.featured_image.url)

        return obj.featured_image.url


class PostDetailSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    author = serializers.StringRelatedField()
    featured_image = serializers.SerializerMethodField()
    media = PostMediaSerializer(many=True, read_only=True)
    meta_tag = MetaTagSerializer(read_only=True)
    json_ld = serializers.SerializerMethodField()
    breadcrumb_ld = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            'id',
            'title',
            'slug',
            'excerpt',
            'content_html',
            'featured',
            'featured_image',
            'category',
            'author',
            'view_count',
            'allow_comments',
            'media',
            'meta_tag',
            'json_ld',
            'breadcrumb_ld',
            'published_at',
            'updated_at',
        )

    def get_featured_image(self, obj):
        if not obj.featured_image:
            return None

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.featured_image.url)

        return obj.featured_image.url

    def get_json_ld(self, obj) -> dict:
        return ArticleSchemaBuilder(obj, request=self.context.get('request')).to_json_ld()

    def get_breadcrumb_ld(self, obj) -> dict:
        return BreadcrumbSchemaBuilder.for_post(obj, request=self.context.get('request')).to_json_ld()

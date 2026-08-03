from rest_framework import serializers

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

    class Meta:
        model = Post
        fields = (
            'id',
            'title',
            'slug',
            'excerpt',
            'content_html',
            'featured_image',
            'category',
            'author',
            'published_at',
            'updated_at',
            'view_count',
            'allow_comments',
            'media',
            'meta_title',
            'meta_description',
        )

    def get_featured_image(self, obj):
        if not obj.featured_image:
            return None

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.featured_image.url)

        return obj.featured_image.url

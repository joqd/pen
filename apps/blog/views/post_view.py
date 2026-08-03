from django.db.models import F
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from ..models.post_model import Post
from ..serializers.post_serializer import (
    PostDetailSerializer,
    PostListSerializer,
)


@extend_schema(tags=['Posts'])
class PostViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Post.published.select_related(
        'author',
        'category',
    ).prefetch_related('media')
    lookup_field = 'slug'
    

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer

        return PostListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        Post.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)

        instance.refresh_from_db(fields=['view_count'])

        serializer = self.get_serializer(instance)

        return Response(serializer.data)

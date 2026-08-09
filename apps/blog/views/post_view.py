from datetime import timedelta

import django_filters
from django.db.models import F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models.post_model import Post
from ..serializers.post_serializer import (
    PostDetailSerializer,
    PostListSerializer,
)


class PostFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='iexact')
    author = django_filters.CharFilter(field_name='author__username', lookup_expr='iexact')

    published_after = django_filters.DateTimeFilter(field_name='published_at', lookup_expr='gte')
    published_before = django_filters.DateTimeFilter(field_name='published_at', lookup_expr='lte')

    min_views = django_filters.NumberFilter(field_name='view_count', lookup_expr='gte')

    period = django_filters.ChoiceFilter(
        method='filter_period',
        choices=[
            ('today', 'Today'),
            ('week', 'This week'),
            ('month', 'This month'),
            ('year', 'This year'),
        ],
    )

    class Meta:
        model = Post
        fields = ['category', 'author', 'featured', 'allow_comments']

    def filter_period(self, queryset, name, value):
        now = timezone.now()
        deltas = {
            'today': timedelta(days=1),
            'week': timedelta(days=7),
            'month': timedelta(days=30),
            'year': timedelta(days=365),
        }
        return queryset.filter(published_at__gte=now - deltas[value])


@extend_schema(tags=['Posts'])
class PostViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Post.published.select_related(
        'author',
        'category',
    ).prefetch_related('media')
    lookup_field = 'slug'

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = PostFilter

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

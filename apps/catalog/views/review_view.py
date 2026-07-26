from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action

from ..models import Review, ReviewStatus, Product
from ..serializers import ReviewReadSerializer, ReviewWriteSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        qs = Review.objects.select_related('user', 'product')

        if not self.request.user.is_staff:
            if self.request.user.is_authenticated:
                from django.db.models import Q
                qs = qs.filter(Q(status=ReviewStatus.APPROVED) | Q(user=self.request.user))
            else:
                qs = qs.filter(status=ReviewStatus.APPROVED)

        product_slug = self.request.query_params.get('product')
        if product_slug:
            qs = qs.filter(product__slug=product_slug)

        return qs

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ReviewWriteSerializer
        return ReviewReadSerializer

    def perform_update(self, serializer):
        if serializer.instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied('You do not have permission to edit this comment.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied('You do not have permission to delete this comment.')
        instance.delete()

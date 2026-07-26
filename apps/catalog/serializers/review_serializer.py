from rest_framework import serializers

from ..models import Product
from ..models import Review, ReviewStatus


class ReviewUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    phone = serializers.CharField()

    class Meta:
        ref_name = 'ReviewUser'


class ReviewProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    slug = serializers.SlugField()


class ReviewReadSerializer(serializers.ModelSerializer):
    user = ReviewUserSerializer(read_only=True)
    product = ReviewProductSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Review
        fields = (
            'id',
            'user',
            'product',
            'rating',
            'comment',
            'status',
            'status_display',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ReviewWriteSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Product.objects.all(),
    )

    class Meta:
        model = Review
        fields = ('id', 'product', 'rating', 'comment')
        read_only_fields = ('id',)

    def validate_product(self, product):
        request = self.context['request']
        qs = Review.objects.filter(user=request.user, product=product)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('You have already reviewed on this product.')
        return product

    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        validated_data['status'] = ReviewStatus.PENDING
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['status'] = ReviewStatus.PENDING
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return ReviewReadSerializer(instance, context=self.context).data
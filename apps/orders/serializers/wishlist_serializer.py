from rest_framework import serializers

from ..models import WishlistItem


class AddWishlistItemSerializer(serializers.Serializer):
    slug = serializers.SlugField()
    

class WishlistItemSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source='product.slug', read_only=True)
    title = serializers.CharField(source='product.title', read_only=True)

    class Meta:
        model = WishlistItem
        fields = ('slug', 'title', 'created_at')
        

class WishlistSerializer(serializers.Serializer):
    items = WishlistItemSerializer(many=True, read_only=True)
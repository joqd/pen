from rest_framework import serializers

from ..models import Cart, CartItem


class AddCartItemSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=64)
    quantity = serializers.IntegerField(min_value=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartItemSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source='variant.sku', read_only=True)
    product_title = serializers.CharField(source='variant.product.title', read_only=True)
    size = serializers.CharField(source='variant.size.name', read_only=True)
    price = serializers.IntegerField(source='variant.price', read_only=True)

    class Meta:
        model = CartItem
        fields = (
            'sku',
            'quantity',
            'product_title',
            'size',
            'price',
        )


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            'id',
            'token',
            'items',
            'total_price',
        )

    def get_total_price(self, obj):
        return sum(item.variant.price * item.quantity for item in obj.items.all())

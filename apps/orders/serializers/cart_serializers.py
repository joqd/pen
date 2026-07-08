from rest_framework import serializers

from ..models import CartItem, Cart


class AddCartItemSerializer(serializers.Serializer):
	variant_id = serializers.IntegerField()
	quantity = serializers.IntegerField(min_value=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='variant.product.title', read_only=True)
    size = serializers.CharField(source='variant.size.name', read_only=True)
    price = serializers.IntegerField(source='variant.price', read_only=True)

    class Meta:
        model = CartItem
        fields = (
            'id', 'quantity',
            'product_title',
            'size', 'price',
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
        return sum(
            item.variant.price * item.quantity
            for item in obj.items.all()
        )
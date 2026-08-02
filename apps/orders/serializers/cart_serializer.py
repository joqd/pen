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
    compare_price = serializers.CharField(source='variant.compare_price', read_only=True)
    image = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()
    size = serializers.CharField(source='variant.size.name', read_only=True)
    price = serializers.IntegerField(source='variant.price', read_only=True)

    class Meta:
        model = CartItem
        fields = (
            'id',
            'sku',
            'image',
            'quantity',
            'product_title',
            'available_stock',
            'size',
            'price',
            'compare_price',
        )
        
    def get_image(self, obj):
        image = (
            obj.variant.product.images.filter(is_primary=True).first()
            or obj.variant.product.images.first()
        )

        if not image:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(image.image.url)

        return image.image.url
    
    def get_available_stock(self, obj):
        return obj.variant.available_stock


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

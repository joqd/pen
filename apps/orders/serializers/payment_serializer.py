from rest_framework import serializers

from apps.accounts.models import Address  # adjust to your actual app layout
from apps.orders.models import Gateway, Order, OrderItem, PaymentTransaction


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'title', 'sku', 'options', 'quantity', 'unit_price', 'total_price']
        read_only_fields = fields


class AddressSerializer(serializers.ModelSerializer):
    """Minimal placeholder — swap for your project's real AddressSerializer."""
    class Meta:
        model = Address
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    is_payable = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'token', 'order_number', 'status', 'shipping_status',
            'subtotal_amount', 'shipping_amount', 'discount_amount', 'total_amount',
            'tracking_code', 'shipping_company', 'customer_note',
            'expires_at', 'paid_at', 'is_payable', 'is_expired',
            'created_at', 'address', 'items',
        ]
        read_only_fields = fields


class CreateOrderSerializer(serializers.Serializer):
    """Input for POST /api/checkout/orders/."""
    address_id = serializers.IntegerField()
    customer_note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_address_id(self, value):
        request = self.context['request']
        if not Address.objects.filter(pk=value, user=request.user).exists():
            raise serializers.ValidationError('این آدرس متعلق به شما نیست یا وجود ندارد.')
        return value


class GatewaySerializer(serializers.ModelSerializer):
    """Public-facing gateway info for the checkout page. Never exposes `credentials`."""
    class Meta:
        model = Gateway
        fields = ['id', 'title', 'badge', 'description', 'min_amount', 'max_amount']
        read_only_fields = fields


class PaymentTransactionSerializer(serializers.ModelSerializer):
    gateway = GatewaySerializer(read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = ['id', 'gateway', 'amount', 'status', 'created_at', 'verified_at']
        read_only_fields = fields


class CreatePaymentSerializer(serializers.Serializer):
    """Input for POST /api/checkout/orders/{token}/pay/."""
    gateway_id = serializers.IntegerField()

    def validate_gateway_id(self, value):
        if not Gateway.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError('درگاه پرداخت انتخاب‌شده معتبر نیست.')
        return value
from rest_framework import serializers

from apps.accounts.models import Address  # adjust to your actual app layout
from apps.orders.models import Gateway, Order, OrderItem, PaymentTransaction


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'title', 'sku', 'options', 'quantity', 'unit_price', 'total_price']
        read_only_fields = fields


class AddressSerializer(serializers.ModelSerializer):
    """Minimal placeholder - swap for your project's real AddressSerializer."""

    class Meta:
        model = Address
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    """Full order representation, used by the retrieve endpoint (single order by token)."""

    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    is_payable = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'token',
            'order_number',
            'status',
            'shipping_status',
            'subtotal_amount',
            'shipping_amount',
            'discount_amount',
            'total_amount',
            'tracking_code',
            'shipping_company',
            'customer_note',
            'expires_at',
            'paid_at',
            'is_payable',
            'is_expired',
            'created_at',
            'address',
            'items',
        ]
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight order representation used by the order *history* / list
    endpoint (`GET /api/orders/`). Deliberately excludes `items` and
    `address` - a customer with dozens of past orders shouldn't pay the
    cost of serializing every line item and address just to render a list.
    Use `OrderSerializer` (retrieve-by-token) for the full detail view.
    """

    is_payable = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    # Expected to be populated via `.annotate(items_count=Count('items'))`
    # on the queryset, so listing orders never triggers one extra query
    # per row.
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'token',
            'order_number',
            'status',
            'shipping_status',
            'total_amount',
            'items_count',
            'is_payable',
            'is_expired',
            'created_at',
        ]
        read_only_fields = fields


class CreateOrderSerializer(serializers.Serializer):
    """Input for POST /api/orders/."""

    address_id = serializers.IntegerField()
    customer_note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_address_id(self, value):
        request = self.context['request']
        if not Address.objects.filter(pk=value, user=request.user).exists():
            raise serializers.ValidationError('This address does not belong to you or does not exist.')
        return value


class OrderAddressUpdateSerializer(serializers.Serializer):
    """Input for PATCH /api/orders/{token}/address/."""

    address_id = serializers.IntegerField()

    def validate_address_id(self, value):
        request = self.context['request']
        if not Address.objects.filter(pk=value, user=request.user).exists():
            raise serializers.ValidationError('This address does not belong to you or does not exist.')
        return value


class AddOrderItemSerializer(serializers.Serializer):
    """Input for POST /api/orders/{token}/items/."""

    sku = serializers.CharField(max_length=64)
    quantity = serializers.IntegerField(min_value=1)


class UpdateOrderItemQuantitySerializer(serializers.Serializer):
    """Input for PATCH /api/orders/{token}/items/{item_id}/."""

    quantity = serializers.IntegerField(min_value=1)


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
    """Input for POST /api/orders/{token}/pay/."""

    gateway_id = serializers.IntegerField()

    def validate_gateway_id(self, value):
        if not Gateway.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError('The selected payment gateway is not valid.')
        return value

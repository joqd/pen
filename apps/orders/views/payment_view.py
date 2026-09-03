from django.conf import settings
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Address  # adjust to your actual app layout
from apps.catalog.models import ProductVariant
from apps.orders.models import Gateway, Order, OrderItem, PaymentTransaction
from apps.orders.serializers.payment_serializer import (
    AddOrderItemSerializer,
    CreateOrderSerializer,
    CreatePaymentSerializer,
    GatewaySerializer,
    OrderAddressUpdateSerializer,
    OrderListSerializer,
    OrderSerializer,
    UpdateOrderItemQuantitySerializer,
)
from apps.orders.services.cart_service import CartService
from apps.orders.services.checkout_service import CheckoutError, create_order_from_cart
from apps.orders.services.checkout_service import add_order_item as checkout_add_order_item
from apps.orders.services.checkout_service import cancel_order as checkout_cancel_order
from apps.orders.services.checkout_service import remove_order_item as checkout_remove_order_item
from apps.orders.services.checkout_service import update_order_address as checkout_update_order_address
from apps.orders.services.checkout_service import update_order_item_quantity as checkout_update_order_item_quantity
from apps.orders.services.payment_service import (
    PaymentCreationError,
    create_payment_transaction,
    handle_payment_callback,
)

# --------------------------------------------------------------------------
# Orders are addressed by their own public UUID `token` everywhere in this
# API - never by the internal integer pk, and (as of this revision) never
# via a "current order" cookie either. Every user can hold any number of
# orders (past purchases, abandoned/expired attempts, orders still pending
# payment); the frontend lists them via `GET /orders/` and operates on a
# specific one via `/orders/{token}/...`. This makes the flow stateless
# and safe across multiple tabs/devices, and lets a returning customer see
# their full order history instead of only the last thing they bought.
# --------------------------------------------------------------------------


class OrderPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(tags=['Orders'])
class OrderListCreateAPIView(APIView):
    """
    GET  /api/orders/  - paginated order history for the authenticated user.
    POST /api/orders/  - create a new order from the user's active cart.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='List my orders',
        description=(
            'Returns a paginated list of every order the authenticated user '
            'has ever placed, most recent first. Supports filtering by '
            '`status` (any value of Order.Status, e.g. `pending_payment`, '
            '`paid`, `cancelled`, `expired`, `refunded`, `processing`).'
        ),
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter orders by status.',
            ),
        ],
        responses={200: OrderListSerializer(many=True)},
    )
    def get(self, request):
        queryset = Order.objects.filter(user=request.user).annotate(items_count=Count('items'))

        status_param = request.query_params.get('status')
        if status_param:
            valid_statuses = dict(Order.Status.choices)
            if status_param not in valid_statuses:
                raise ValidationError({'status': [f'Invalid status. Choose from: {", ".join(valid_statuses)}.']})
            queryset = queryset.filter(status=status_param)

        paginator = OrderPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = OrderListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary='Create an order from the active cart',
        description=(
            "Converts the authenticated user's active Cart into a new "
            'Order. This is the step the checkout page calls right after '
            'the user confirms their shipping address, and before they '
            'pick a payment gateway.\n\n'
            'Not tied to any "current order" state: calling this again '
            'later (after adding new items to the cart) simply creates '
            'another, independent order - a customer can have many orders '
            'over time, and several PENDING_PAYMENT ones at once.'
        ),
        request=CreateOrderSerializer,
        responses={
            201: OpenApiResponse(response=OrderSerializer, description='Order created successfully.'),
            400: OpenApiResponse(
                description=(
                    'Address validation error (`address_id`), or a business-logic '
                    'error (`detail`) such as an empty cart or an out-of-stock item.'
                ),
                examples=[
                    OpenApiExample('Invalid address', value={'address_id': ['Address not found.']}),
                    OpenApiExample('Empty cart', value={'detail': 'Cart is empty'}),
                ],
            ),
            401: OpenApiResponse(description='No authenticated user.'),
        },
    )
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        cart = CartService.get_or_create_cart(user=request.user)
        address = Address.objects.get(pk=serializer.validated_data['address_id'])

        try:
            order = create_order_from_cart(
                cart=cart,
                address=address,
                customer_note=serializer.validated_data['customer_note'],
            )
        except CheckoutError as exc:
            raise ValidationError({'detail': str(exc)})

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Orders'],
    summary='Retrieve a specific order',
    description='Returns full detail for one order, identified by its public `token`. Must belong to the caller.',
    parameters=[OpenApiParameter(name='token', type=str, location=OpenApiParameter.PATH)],
    responses={200: OrderSerializer, 404: OpenApiResponse(description='No such order for this user.')},
)
class OrderDetailAPIView(APIView):
    """GET /api/orders/{token}/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        order = get_object_or_404(
            Order.objects.select_related('address').prefetch_related('items'),
            token=token,
            user=request.user,
        )
        return Response(OrderSerializer(order).data)


@extend_schema(
    tags=['Orders'],
    summary='Cancel a pending order',
    description=(
        'Cancels an order that is still `pending_payment` and releases its '
        'reserved stock. Orders that are already paid, expired, cancelled, '
        'or refunded cannot be cancelled through this endpoint.'
    ),
    parameters=[OpenApiParameter(name='token', type=str, location=OpenApiParameter.PATH)],
    responses={
        200: OrderSerializer,
        400: OpenApiResponse(description='Order is not in a cancellable state.'),
        404: OpenApiResponse(description='No such order for this user.'),
    },
)
class OrderCancelAPIView(APIView):
    """POST /api/orders/{token}/cancel/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        order = get_object_or_404(Order, token=token, user=request.user)

        checkout_cancel_order(order.pk)
        order.refresh_from_db()

        if order.status != Order.Status.CANCELLED:
            raise ValidationError({'detail': 'Only orders that are pending payment can be cancelled.'})

        return Response(OrderSerializer(order).data)


@extend_schema(
    tags=['Orders'],
    summary="Change a pending order's shipping address",
    description=(
        'Updates the address of an order that is still `pending_payment` '
        '(and not expired). Any PENDING payment attempt on this order is '
        'invalidated - the gateway session it points to was created for '
        'the old address/total and can no longer be trusted, so the '
        'frontend must call `pay/` again after this to start a fresh one.'
    ),
    parameters=[OpenApiParameter(name='token', type=str, location=OpenApiParameter.PATH)],
    request=OrderAddressUpdateSerializer,
    responses={
        200: OrderSerializer,
        400: OpenApiResponse(description='Invalid address, or order is no longer editable.'),
        404: OpenApiResponse(description='No such order for this user.'),
    },
)
class OrderAddressUpdateAPIView(APIView):
    """PATCH /api/orders/{token}/address/"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, token):
        order = get_object_or_404(Order, token=token, user=request.user)

        serializer = OrderAddressUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        address = Address.objects.get(pk=serializer.validated_data['address_id'])

        try:
            order = checkout_update_order_address(order_id=order.pk, address=address)
        except CheckoutError as exc:
            raise ValidationError({'detail': str(exc)})

        return Response(OrderSerializer(order).data)


@extend_schema(
    tags=['Orders'],
    summary='Add an item to a pending order',
    description=(
        'Adds a new line item (by variant SKU) to an order that is still '
        '`pending_payment`. Reserves stock for it and recalculates order '
        'totals. Fails if the item is already on the order (use the update '
        'endpoint to change its quantity instead) or if stock is '
        'insufficient. Invalidates any PENDING payment attempt, same as '
        'address changes.'
    ),
    parameters=[OpenApiParameter(name='token', type=str, location=OpenApiParameter.PATH)],
    request=AddOrderItemSerializer,
    responses={
        201: OrderSerializer,
        400: OpenApiResponse(description='Item already on the order, out of stock, or order no longer editable.'),
        404: OpenApiResponse(description='No such order for this user, or no such SKU.'),
    },
)
class OrderItemCreateAPIView(APIView):
    """POST /api/orders/{token}/items/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        order = get_object_or_404(Order, token=token, user=request.user)

        serializer = AddOrderItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = get_object_or_404(
            ProductVariant.objects.filter(is_active=True),
            sku=serializer.validated_data['sku'],
        )

        try:
            checkout_add_order_item(
                order_id=order.pk,
                variant=variant,
                quantity=serializer.validated_data['quantity'],
            )
        except CheckoutError as exc:
            raise ValidationError({'detail': str(exc)})

        order.refresh_from_db()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Orders'],
    summary='Update or remove a line item on a pending order',
    description=(
        'PATCH changes the quantity of an existing line item. DELETE '
        'removes it entirely (refused if it is the last remaining item - '
        'cancel the order instead). Both are only allowed while the order '
        'is `pending_payment`, adjust reserved stock and totals '
        'accordingly, and invalidate any PENDING payment attempt.'
    ),
    parameters=[
        OpenApiParameter(name='token', type=str, location=OpenApiParameter.PATH),
        OpenApiParameter(name='item_id', type=int, location=OpenApiParameter.PATH),
    ],
)
class OrderItemUpdateDeleteAPIView(APIView):
    """PATCH/DELETE /api/orders/{token}/items/{item_id}/"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, token, item_id):
        order = get_object_or_404(Order, token=token, user=request.user)

        serializer = UpdateOrderItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            checkout_update_order_item_quantity(
                order_id=order.pk,
                item_id=item_id,
                quantity=serializer.validated_data['quantity'],
            )
        except OrderItem.DoesNotExist:
            raise ValidationError({'detail': 'No such item on this order.'})
        except CheckoutError as exc:
            raise ValidationError({'detail': str(exc)})

        order.refresh_from_db()
        return Response(OrderSerializer(order).data)

    def delete(self, request, token, item_id):
        order = get_object_or_404(Order, token=token, user=request.user)

        try:
            checkout_remove_order_item(order_id=order.pk, item_id=item_id)
        except OrderItem.DoesNotExist:
            raise ValidationError({'detail': 'No such item on this order.'})
        except CheckoutError as exc:
            raise ValidationError({'detail': str(exc)})

        order.refresh_from_db()
        return Response(OrderSerializer(order).data)


@extend_schema(
    tags=['Checkout'],
    summary='List active payment gateways',
    description=(
        'Lists currently active payment gateways (`is_active=True`), ordered '
        'by priority (model default ordering), for the "choose a payment '
        'method" step of checkout. `credentials` is never serialized - only '
        'id/title/badge/description/min_amount/max_amount reach the frontend.'
    ),
    responses={
        200: OpenApiResponse(response=GatewaySerializer(many=True)),
        401: OpenApiResponse(description='No authenticated user.'),
    },
)
class ActiveGatewayListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        gateways = Gateway.objects.filter(is_active=True)
        serializer = GatewaySerializer(gateways, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema(
    tags=['Checkout'],
    summary='Start or resume a payment attempt for an order',
    description=(
        'Starts (or resumes) a payment attempt against the chosen gateway '
        'for the order identified by `token`, and returns a URL to send the '
        'browser to. The only thing the frontend sends is the gateway the '
        'user picked (`gateway_id`).\n\n'
        'The frontend must perform a full-page redirect '
        '(`window.location.href = redirect_url`), not a client-side route '
        "change - the user is leaving the app for the gateway's own site.\n\n"
        '**Notes:**\n'
        '- Safe to call more than once: if a PENDING transaction already '
        'exists for this order, the same `redirect_url` is returned rather '
        'than creating a second payment session (also enforced at the DB '
        'level via a partial unique constraint on `PaymentTransaction`).\n'
        '- Because payment is scoped to a specific order token (not a '
        'single "current order"), a user may have several different orders '
        'open for payment in different tabs at the same time.\n'
        '- The `callback_url` sent to the gateway always points to the '
        "backend's own callback endpoint - the gateway never talks to the "
        'frontend directly.'
    ),
    parameters=[OpenApiParameter(name='token', type=str, location=OpenApiParameter.PATH)],
    request=CreatePaymentSerializer,
    responses={
        200: OpenApiResponse(
            description='Redirect URL to the payment gateway.',
            examples=[
                OpenApiExample('Success', value={'redirect_url': 'https://www.zarinpal.com/pg/StartPay/A00000...'})
            ],
        ),
        400: OpenApiResponse(description='Invalid/inactive gateway (`gateway_id`), or order no longer payable.'),
        404: OpenApiResponse(description='No such order for this user.'),
        401: OpenApiResponse(description='No authenticated user.'),
    },
)
class PaymentCreateAPIView(APIView):
    """POST /api/orders/{token}/pay/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        order = get_object_or_404(Order, token=token, user=request.user)

        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gateway = Gateway.objects.get(pk=serializer.validated_data['gateway_id'])

        try:
            _transaction, redirect_url = create_payment_transaction(order=order, gateway=gateway, request=request)
        except PaymentCreationError as exc:
            raise ValidationError({'detail': str(exc)})

        return Response({'redirect_url': redirect_url})


@extend_schema(
    tags=['Payments'],
    summary='Payment gateway return callback',
    description=(
        "Public endpoint (no auth) the gateway redirects the buyer's browser "
        'to after they complete or cancel payment (e.g. Zarinpal calling back '
        'with `?Authority=...&Status=OK`). There is no session/JWT on this '
        "request - the browser arrives here straight from the gateway's "
        'domain - so this view must not assume an authenticated user exists.\n\n'
        'The transaction is looked up by `Authority` (the identifier the '
        'gateway itself hands back). All business logic lives in '
        '`services.handle_payment_callback()`, which is idempotent (safe to '
        'run twice for the same Authority) since gateways occasionally fire '
        'the callback more than once and users sometimes refresh the '
        'landing page mid-flow.\n\n'
        'This view never returns JSON: it performs an HTTP redirect straight '
        "to the frontend's order-result page, addressed by the order's own "
        'token (a random, unguessable UUID - not a secret, ownership is '
        're-checked by every authenticated endpoint the frontend calls '
        'next). The frontend re-fetches the real status from '
        '`GET /api/orders/{token}/` rather than trusting the `status` query '
        'string on this redirect, which is attacker-controllable.'
    ),
    parameters=[
        OpenApiParameter(
            name='gateway_origin',
            type=str,
            location=OpenApiParameter.PATH,
            description='Identifier of the originating gateway (e.g. zarinpal).',
        ),
        OpenApiParameter(name='Authority', type=str, location=OpenApiParameter.QUERY, required=False),
        OpenApiParameter(name='Status', type=str, location=OpenApiParameter.QUERY, required=False),
    ],
    responses={
        302: OpenApiResponse(
            description=(
                'Redirect to the frontend result page: '
                '`{FRONTEND_BASE_URL}/orders/{token}/result?status=success|failed`, or, '
                'if the Authority could not be matched to any transaction: '
                '`{FRONTEND_BASE_URL}/orders/result?status=error`.'
            ),
        ),
    },
)
class PaymentCallbackAPIView(APIView):
    """GET /api/payments/callback/{gateway_origin}/"""

    permission_classes = [AllowAny]

    def get(self, request, gateway_origin):
        authority = request.query_params.get('Authority', '')
        gateway_status = request.query_params.get('Status', '')

        try:
            payment_transaction = handle_payment_callback(
                gateway_origin=gateway_origin,
                authority=authority,
                gateway_status=gateway_status,
            )
        except PaymentCreationError:
            return HttpResponseRedirect(f'{settings.FRONTEND_BASE_URL}/orders/result?status=error')

        order = payment_transaction.order
        result = 'success' if payment_transaction.status == PaymentTransaction.Status.SUCCESS else 'failed'
        return HttpResponseRedirect(f'{settings.FRONTEND_BASE_URL}/orders/{order.token}/result?status={result}')

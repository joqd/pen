from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Address  # adjust to your actual app layout
from apps.orders.models import Gateway, Order, PaymentTransaction
from apps.orders.serializers.payment_serializer import (
    CreateOrderSerializer,
    CreatePaymentSerializer,
    GatewaySerializer,
    OrderSerializer,
)
from apps.orders.services.payment_service import (
    OrderCreationError,
    PaymentCreationError,
    create_order_from_cart,
    create_payment_transaction,
    handle_payment_callback,
)

# --------------------------------------------------------------------------
# Order-token cookie handling.
#
# The order token is never expected from the frontend anymore (no path
# param, no body field). It's written to an HttpOnly cookie right after
# order creation and read back from that same cookie by every other view
# that needs to resolve "the current order". This keeps the token out of
# JS-accessible storage (localStorage/sessionStorage) and out of URLs.
# --------------------------------------------------------------------------
ORDER_TOKEN_COOKIE = 'order_token'
ORDER_TOKEN_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days — matches how long an abandoned order can be resumed


def set_order_token_cookie(response, order):
    """Attach/refresh the HttpOnly order-token cookie on `response`."""
    response.set_cookie(
        key=ORDER_TOKEN_COOKIE,
        value=str(order.token),
        max_age=ORDER_TOKEN_COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,  # must be True in production (HTTPS)
        samesite='Lax',  # switch to 'None' (+ secure=True) if frontend/backend are cross-site
        path='/',
    )
    return response


def get_order_or_404_from_cookie(request):
    """Resolve the caller's current Order from the `order_token` cookie."""
    token = request.COOKIES.get(ORDER_TOKEN_COOKIE)
    if not token:
        raise NotFound('No active order found. Please start checkout again.')
    return get_object_or_404(Order, token=token, user=request.user)


@extend_schema(
    tags=['Checkout'],
    summary='Create an order from the active cart',
    description=(
        "Converts the authenticated user's active Cart into an Order. This is "
        'the step the checkout page calls right after the user confirms their '
        'shipping address, and before they pick a payment gateway.\n\n'
        'On success, the order token is set as an **HttpOnly cookie** '
        f'(`{ORDER_TOKEN_COOKIE}`) on the response — the frontend does not '
        'need to read, store, or resend it. Every later checkout call '
        '(payment, order detail) resolves the order from that cookie '
        'automatically.\n\n'
        '**Notes:**\n'
        '- Not safely repeatable: calling this twice in a row with the same '
        'cart fails the second time with an "cart already converted" error. '
        'If the frontend needs a retry affordance, it should re-fetch the '
        'existing order via `GET /api/orders/current/` instead of calling '
        'this endpoint again.\n'
        '- This endpoint intentionally does not accept a gateway choice or '
        'trigger any payment — order creation and payment are separate steps '
        'so a user can create an order, abandon it, and come back later to pay.'
    ),
    request=CreateOrderSerializer,
    responses={
        201: OpenApiResponse(
            response=OrderSerializer,
            description=(
                'Order created successfully. The order token is also set as '
                f'an HttpOnly `{ORDER_TOKEN_COOKIE}` cookie on this response.'
            ),
        ),
        400: OpenApiResponse(
            description=(
                'Address validation error (`address_id`), or a business-logic '
                'error (`detail`) such as an empty cart, an already-converted '
                'cart, or an out-of-stock item.'
            ),
            examples=[
                OpenApiExample(
                    'Invalid address',
                    value={'address_id': ['Address not found.']},
                ),
                OpenApiExample(
                    'Cart already converted',
                    value={'detail': 'This cart has already been converted into an order.'},
                ),
            ],
        ),
        401: OpenApiResponse(description='No authenticated user.'),
    },
)
class OrderCreateAPIView(APIView):
    """POST /api/checkout/orders/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        cart = get_object_or_404(request.user.cart.__class__, user=request.user)
        address = Address.objects.get(pk=serializer.validated_data['address_id'])

        try:
            order = create_order_from_cart(
                cart=cart,
                user=request.user,
                address=address,
                customer_note=serializer.validated_data['customer_note'],
            )
        except OrderCreationError as exc:
            raise ValidationError({'detail': str(exc)})

        response = Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return set_order_token_cookie(response, order)


@extend_schema(
    tags=['Orders'],
    summary='Retrieve the current order (from cookie)',
    description=(
        "Returns the current, authoritative state of the caller's active "
        f'order, resolved from the `{ORDER_TOKEN_COOKIE}` HttpOnly cookie set '
        'during order creation — no token is passed by the frontend.\n\n'
        'This is what the order-result page calls after a gateway redirect. '
        'The frontend must NOT trust the `?status=` query string on the '
        'redirect URL by itself — that string is attacker-controllable (a '
        'user can edit the URL). Always re-fetch here and branch UI on '
        '`order.status`.'
    ),
    parameters=[
        OpenApiParameter(
            name=ORDER_TOKEN_COOKIE,
            type=str,
            location=OpenApiParameter.COOKIE,
            # required=True,
            description='HttpOnly cookie set by `POST /api/checkout/orders/`. Sent automatically by the browser.',
        ),
    ],
    responses={
        200: OrderSerializer,
        404: OpenApiResponse(description='No `order_token` cookie present, or no matching order for this user.'),
        401: OpenApiResponse(description='No authenticated user.'),
    },
)
class OrderDetailAPIView(APIView):
    """GET /api/orders/current/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        order = get_order_or_404_from_cookie(request)
        return Response(OrderSerializer(order).data)


@extend_schema(
    tags=['Checkout'],
    summary='List active payment gateways',
    description=(
        'Lists currently active payment gateways (`is_active=True`), ordered '
        'by priority (model default ordering), for the "choose a payment '
        'method" step of checkout. `credentials` is never serialized — only '
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

        serializer = GatewaySerializer(
            gateways,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)


@extend_schema(
    tags=['Checkout'],
    summary='Start or resume a payment attempt for the current order',
    description=(
        'Starts (or resumes) a payment attempt against the chosen gateway for '
        f'the order resolved from the `{ORDER_TOKEN_COOKIE}` cookie, and '
        'returns a URL to send the browser to. The only thing the frontend '
        'sends is the gateway the user picked (`gateway_id`).\n\n'
        'The frontend must perform a full-page redirect '
        '(`window.location.href = redirect_url`), not a client-side route '
        "change — the user is leaving the app for the gateway's own site.\n\n"
        '**Notes:**\n'
        '- Safe to call more than once: if a PENDING transaction already '
        'exists for this order, the same `redirect_url` is returned rather '
        'than creating a second payment session (also enforced at the DB '
        'level via a partial unique constraint on `PaymentTransaction`).\n'
        '- The `callback_url` sent to the gateway always points to the '
        "backend's own callback endpoint — the gateway never talks to the "
        'frontend directly.'
    ),
    parameters=[
        OpenApiParameter(
            name=ORDER_TOKEN_COOKIE,
            type=str,
            location=OpenApiParameter.COOKIE,
            # required=True,
            description='HttpOnly cookie identifying the order being paid for. Sent automatically by the browser.',
        ),
    ],
    request=CreatePaymentSerializer,
    responses={
        200: OpenApiResponse(
            description='Redirect URL to the payment gateway.',
            examples=[
                OpenApiExample(
                    'Success',
                    value={'redirect_url': 'https://www.zarinpal.com/pg/StartPay/A00000...'},
                ),
            ],
        ),
        400: OpenApiResponse(
            description='Invalid/inactive gateway (`gateway_id`).',
        ),
        404: OpenApiResponse(description='No `order_token` cookie present, or no matching order for this user.'),
        401: OpenApiResponse(description='No authenticated user.'),
    },
)
class PaymentCreateAPIView(APIView):
    """POST /api/checkout/orders/pay/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        order = get_order_or_404_from_cookie(request)

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
        "request — the browser arrives here straight from the gateway's "
        'domain — so this view must not assume an authenticated user exists.\n\n'
        'The transaction is looked up by `Authority` (the identifier the '
        "gateway itself hands back), **not** by cookie — that's the only "
        'reliable way to tie this callback to the right payment attempt. '
        'The `order_token` cookie is then (re)set on the redirect response so '
        "it's guaranteed correct for the page the user lands on next.\n\n"
        'All business logic lives in `services.handle_payment_callback()`, '
        'which is idempotent (safe to run twice for the same Authority) since '
        'gateways occasionally fire the callback more than once and users '
        'sometimes refresh the landing page mid-flow.\n\n'
        'This view never returns JSON: it performs an HTTP redirect straight '
        'to the frontend result page, passing only a coarse status hint — no '
        'order token in the URL, since the cookie already carries it. The '
        'frontend re-fetches the real status from `GET /api/orders/current/` '
        'rather than trusting this query string.'
    ),
    parameters=[
        OpenApiParameter(
            name='gateway_origin',
            type=str,
            location=OpenApiParameter.PATH,
            description='Identifier of the originating gateway (e.g. zarinpal).',
        ),
        OpenApiParameter(
            name='Authority',
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Transaction identifier returned by the gateway.',
        ),
        OpenApiParameter(
            name='Status',
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Raw status sent by the gateway (e.g. OK/NOK).',
        ),
    ],
    responses={
        302: OpenApiResponse(
            description=(
                'Redirect to the frontend result page: '
                '`{FRONTEND_BASE_URL}/orders/result?status=success|failed`, with '
                f'the `{ORDER_TOKEN_COOKIE}` cookie (re)set on this response, '
                'or, if the Authority could not be matched to any transaction: '
                '`{FRONTEND_BASE_URL}/orders/result?status=error` (cookie left untouched).'
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
        response = HttpResponseRedirect(f'{settings.FRONTEND_BASE_URL}/orders/result?status={result}')
        return set_order_token_cookie(response, order)

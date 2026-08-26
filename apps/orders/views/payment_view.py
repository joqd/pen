from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
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


class OrderCreateAPIView(APIView):
    """
    POST /api/checkout/orders/

    Turns the authenticated user's active Cart into an Order. This is the
    step the Next.js checkout page calls right after the user confirms
    their shipping address, and before they pick a payment gateway.

    Request body:
        {
            "address_id": 12,
            "customer_note": "زنگ در خراب است"   # optional
        }

    Responses:
        201 Created
            Full OrderSerializer payload. The frontend must store
            `order.token` (a UUID) — every later call (payment, order
            detail, result page) is keyed on this token, never on a
            numeric id.
        400 Bad Request
            {"address_id": [...]}  — the address doesn't belong to the
            user / doesn't exist, OR
            {"detail": "..."}      — OrderCreationError from the service
            layer (empty cart, cart already converted, an item is out of
            stock, ...). Show `detail` to the user as-is; it's already a
            Persian, user-facing message.
        401 Unauthorized
            No authenticated user.

    Notes:
        - Idempotency: calling this twice in a row with the same cart will
          fail the second time with "این سبد قبلاً به سفارش تبدیل شده
          است." (the cart's `converted_at` is set on success). If the
          frontend needs a "retry" affordance, it should re-fetch the
          existing order via GET /api/orders/{token}/ instead of calling
          this endpoint again.
        - This view intentionally does NOT accept `gateway_id` or trigger
          any payment — order creation and payment are separate steps so
          a user can create an order, abandon it, and come back later to
          pay (see PaymentCreateAPIView).
    """
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

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailAPIView(APIView):
    """
    GET /api/orders/{token}/

    Returns the current, authoritative state of a single order, looked up
    by its public `token` rather than its numeric id.

    This is what the Next.js order-result page
    (`app/orders/[token]/result/page.tsx`) calls after a gateway redirect.
    The page must NOT trust the `?status=` query string on the redirect
    URL by itself — that string is attacker-controllable (a user can edit
    the URL). Always re-fetch here and branch UI on `order.status`.

    Responses:
        200 OK  -> OrderSerializer payload.
        404 Not Found -> no such order, or it belongs to a different user.
        401 Unauthorized -> no authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        order = get_object_or_404(Order, token=token, user=request.user)
        return Response(OrderSerializer(order).data)


class ActiveGatewayListAPIView(APIView):
    """
    GET /api/checkout/gateways/

    Lists currently active payment gateways (`is_active=True`), ordered by
    `priority` (model default ordering), for the "choose a payment method"
    step of checkout. `credentials` is never serialized — only
    id/title/badge/description/min_amount/max_amount reach the frontend.

    Responses:
        200 OK -> [GatewaySerializer, ...]
        401 Unauthorized -> no authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        gateways = Gateway.objects.filter(is_active=True)
        return Response(GatewaySerializer(gateways, many=True).data)


class PaymentCreateAPIView(APIView):
    """
    POST /api/checkout/orders/{token}/pay/

    Starts (or resumes) a payment attempt for the given order against the
    chosen gateway and returns a URL to send the browser to.

    Request body:
        {"gateway_id": 1}

    Responses:
        200 OK
            {"redirect_url": "https://www.zarinpal.com/pg/StartPay/A00000..."}
            The frontend must do a full-page redirect
            (`window.location.href = redirect_url`), not a client-side
            route change — the user is leaving your app for the gateway's
            own site.
        400 Bad Request
            {"gateway_id": [...]}  — invalid/inactive gateway, OR
            {"detail": "..."}      — PaymentCreationError (order already
            paid/expired, or the gateway API itself failed). Show
            `detail` to the user; on a gateway failure it's safe to offer
            a "try again" button that re-calls this same endpoint.
        404 Not Found
            No such order for this user.
        401 Unauthorized
            No authenticated user.

    Notes:
        - Safe to call more than once: if a PENDING transaction already
          exists for this order, the SAME redirect_url is returned rather
          than creating a second payment session (also enforced at the DB
          level via a partial unique constraint on PaymentTransaction).
        - `callback_url` sent to the gateway is always the backend's own
          `/api/payments/callback/{gateway_origin}/` — the gateway never
          talks to the Next.js frontend directly.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        order = get_object_or_404(Order, token=token, user=request.user)

        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gateway = Gateway.objects.get(pk=serializer.validated_data['gateway_id'])

        try:
            _transaction, redirect_url = create_payment_transaction(
                order=order, gateway=gateway, request=request
            )
        except PaymentCreationError as exc:
            raise ValidationError({'detail': str(exc)})

        return Response({'redirect_url': redirect_url})


class PaymentCallbackAPIView(APIView):
    """
    GET /api/payments/callback/{gateway_origin}/

    Public endpoint (no auth) the gateway redirects the buyer's browser to
    after they complete or cancel payment, e.g. Zarinpal calling back with
    `?Authority=A00000...&Status=OK`. There is no session/JWT of ours on
    this request — the browser arrives here straight from the gateway's
    domain — so this view must not assume `request.user` exists.

    All business logic lives in `services.handle_payment_callback()`,
    which is idempotent (safe to run twice for the same Authority) since
    gateways occasionally fire the callback more than once and users
    sometimes refresh the landing page mid-flow.

    This view never returns JSON: it performs an HTTP redirect straight to
    the Next.js result page, passing only the order token and a coarse
    status hint. The frontend re-fetches the real status from
    GET /api/orders/{token}/ rather than trusting this query string.

    Responses:
        302 Found -> redirects to
            "{FRONTEND_BASE_URL}/orders/{order.token}/result?status=success|failed", or
            "{FRONTEND_BASE_URL}/orders/result?status=error" if the
            Authority couldn't be matched to any transaction at all
            (e.g. a forged/garbage callback).
    """
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
        return HttpResponseRedirect(
            f'{settings.FRONTEND_BASE_URL}/orders/{order.token}/result?status={result}'
        )
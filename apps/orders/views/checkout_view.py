from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order, PaymentTransaction
from apps.orders.services.checkout_service import (
    EmptyCartError,
    OutOfStockError,
    create_order_from_cart,
    finalize_paid_order,
    release_reserved_stock,
)
from apps.orders.services.payment_service import AqayePardakhtGateway, PaymentGatewayError


class CheckoutInitiateView(APIView):
    """
    POST /orders/checkout/
    body: {"address_id": <int>, "note": <str, optional>}

    Cookie-session auth (SessionAuthentication) is assumed to be active in
    DRF settings, so `request.user` is resolved from the session cookie the
    NextJS app forwards with `credentials: 'include'`. Because this is a
    state-changing POST, the frontend must also send the CSRF token
    (read from the `csrftoken` cookie) in the `X-CSRFToken` header.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Checkout'])
    def post(self, request):
        address_id = request.data.get('address_id')
        try:
            address = request.user.addresses.get(pk=address_id)
        except ObjectDoesNotExist:
            return Response({'address_id': 'Invalid address'}, status=status.HTTP_400_BAD_REQUEST)

        cart = getattr(request.user, 'cart', None)
        if cart is None:
            return Response({'detail': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = create_order_from_cart(cart=cart, address=address, customer_note=request.data.get('note', ''))
        except OutOfStockError as exc:
            return Response(
                {'detail': str(exc), 'variant_sku': exc.variant.sku},
                status=status.HTTP_409_CONFLICT,
            )
        except EmptyCartError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        gateway = AqayePardakhtGateway()
        try:
            transid, pay_url = gateway.request_payment(order=order)
        except PaymentGatewayError as exc:
            # Order stays PENDING_PAYMENT and will simply expire via the
            # sweep task if the customer never gets a working pay_url;
            # nothing needs to be rolled back manually here.
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        PaymentTransaction.objects.create(order=order, authority=transid, amount=order.total_amount)

        return Response(
            {
                'order_number': order.order_number,
                'total_amount': order.total_amount,
                'expires_at': order.expires_at,
                'payment_url': pay_url,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentCallbackView(APIView):
    """
    Aqaye Pardakht redirects the buyer back to the `callback` URL you gave
    at /create time, POSTing a single field: `transid`. There is NO
    separate success/fail flag in the callback itself - you always have to
    call /verify and read `code` from that response to know the outcome.
    We keep our own `order` token as a query param on the callback URL
    (added when building it in AqayePardakhtGateway._callback_url) so this
    view can look the order up; some deployments of this gateway send the
    callback as GET instead of POST, so we accept transid from either.

    Public (no auth) - the gateway itself calls this, not the browser
    session. Everything is scoped and locked by (order token + transid) so
    it can't be used to tamper with someone else's order.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=['Checkout'])
    def get(self, request):
        return self._handle(request)

    @extend_schema(tags=['Checkout'])
    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        order_token = request.GET.get('order')
        transid = request.POST.get('transid') or request.GET.get('transid', '')

        order = Order.objects.filter(token=order_token).first()
        if not order:
            return redirect(f'{settings.FRONTEND_BASE_URL}/checkout/failed?reason=not_found')

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            txn = order.transactions.select_for_update().filter(authority=transid).first()

            # Idempotency guard: the gateway (or the user hitting back/
            # refresh) may call this more than once. If we've already
            # resolved this order/transaction, just redirect to whatever
            # the final state already is instead of re-verifying and
            # re-applying stock changes.
            already_resolved = (
                order.status != Order.Status.PENDING_PAYMENT
                or txn is None
                or txn.status != PaymentTransaction.Status.PENDING
            )
            if already_resolved:
                return redirect(self._result_url(order))

            gateway = AqayePardakhtGateway()
            try:
                result = gateway.verify_payment(transid=transid, amount=order.total_amount)
            except PaymentGatewayError as exc:
                self._fail(order, txn, exc)
                return redirect(self._result_url(order))

            txn.status = PaymentTransaction.Status.SUCCESS
            txn.raw_response = result
            txn.verified_at = timezone.now()
            txn.save(update_fields=['status', 'raw_response', 'verified_at'])

            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=['status', 'paid_at'])

            finalize_paid_order(order)

        return redirect(self._result_url(order))

    @staticmethod
    def _fail(order: Order, txn: PaymentTransaction | None, exc: PaymentGatewayError | None = None) -> None:
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status'])
        if txn:
            txn.status = PaymentTransaction.Status.FAILED
            if exc is not None and exc.payload:
                txn.raw_response = exc.payload
                txn.save(update_fields=['status', 'raw_response'])
            else:
                txn.save(update_fields=['status'])
        release_reserved_stock(order)

    @staticmethod
    def _result_url(order: Order) -> str:
        base = settings.FRONTEND_BASE_URL.rstrip('/')
        if order.status == Order.Status.PAID:
            return f'{base}/checkout/success?order={order.order_number}'
        return f'{base}/checkout/failed?order={order.order_number}'

"""
Business logic for taking an already-created Order through payment.

NOTE: Order creation itself (turning a Cart into an Order + reserving
stock) intentionally does NOT live here anymore - it lives in
`checkout_service.create_order_from_cart`, which is the concurrency-safe
(SELECT ... FOR UPDATE) implementation. This module used to have its own,
weaker, duplicate copy of that logic (no row locking, no item snapshot on
some fields); that duplication was a real bug risk (the two copies could
silently drift apart) and has been removed in favor of a single source of
truth. This module now only deals with the *payment* side: starting a
gateway payment attempt and processing the gateway's callback.

NOTE on imports: adjust these to match your actual app layout. This file
assumes Gateway/Order/PaymentTransaction are importable from
`apps.orders.models`.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Gateway, Order, PaymentTransaction
from apps.orders.services.checkout_service import finalize_paid_order
from apps.payments.adapters.base import GatewayAdapterError
from apps.payments.adapters.registery import get_adapter

logger = logging.getLogger(__name__)

PENDING_TRANSACTION_TIMEOUT_MINUTES = getattr(settings, 'PENDING_TRANSACTION_TIMEOUT_MINUTES', 20)


class PaymentCreationError(Exception):
    """Raised when a payment attempt can't be started (order not payable, gateway failure, ...)."""


@transaction.atomic
def create_payment_transaction(*, order: Order, gateway: Gateway, request) -> tuple[PaymentTransaction, str]:
    """
    Start (or resume) a payment attempt for `order` against `gateway`.

    - Rejects orders that are no longer payable (already paid / expired) -
      checked again here under a row lock, not just relying on whatever
      the caller believed.
    - If a PENDING transaction already exists for this order (this is also
      enforced at the DB level by `unique_pending_transaction_per_order`),
      it's reused instead of creating a duplicate: a user clicking "pay"
      twice gets redirected to the same payment session, not two of them.
    - Delegates the actual gateway call to `get_adapter(gateway)`, so this
      function has zero gateway-specific logic.
    - Because each Order has its own independent `PaymentTransaction`
      history, a user can have several PENDING_PAYMENT orders at once and
      pay them off in any order/tab - there is no longer a single "the
      current order" concept anywhere in this flow.

    Returns (transaction, redirect_url). Raises PaymentCreationError on
    any business-rule violation or gateway-side failure.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)

    if not order.is_payable:
        raise PaymentCreationError('This order is no longer payable (already paid or expired).')

    adapter = get_adapter(gateway)

    existing = order.transactions.filter(status=PaymentTransaction.Status.PENDING).first()
    if existing is not None and existing.authority:
        return existing, f'{adapter.startpay_url}{existing.authority}'

    payment_transaction = PaymentTransaction.objects.create(
        order=order,
        gateway=gateway,
        amount=order.total_amount,
        expires_at=timezone.now() + timezone.timedelta(minutes=PENDING_TRANSACTION_TIMEOUT_MINUTES),
    )

    callback_url = request.build_absolute_uri(f'/api/payments/callback/{gateway.origin}/')

    try:
        result = adapter.request_payment(
            amount=payment_transaction.amount,
            callback_url=callback_url,
            description=f'Payment for order {order.order_number}',
            mobile=getattr(order.user, 'phone', '') or '',
        )
    except GatewayAdapterError as exc:
        payment_transaction.status = PaymentTransaction.Status.FAILED
        payment_transaction.raw_response = {'error': str(exc)}
        payment_transaction.save(update_fields=['status', 'raw_response', 'updated_at'])
        logger.warning('Payment request failed for order %s: %s', order.order_number, exc)
        raise PaymentCreationError('Could not reach the payment gateway. Please try again.') from exc

    payment_transaction.authority = result.authority
    payment_transaction.raw_response = result.raw_response
    payment_transaction.save(update_fields=['authority', 'raw_response', 'updated_at'])

    return payment_transaction, result.redirect_url


@transaction.atomic
def handle_payment_callback(*, gateway_origin: str, authority: str, gateway_status: str) -> PaymentTransaction:
    """
    Process a gateway's redirect-back callback
    (e.g. Zarinpal's `?Authority=...&Status=OK|NOK`).

    Idempotent by design: if the transaction has already left the PENDING
    state (a previous call already resolved it), it's returned unchanged
    without calling the gateway's verify endpoint again - gateways
    sometimes hit the callback more than once, and users refresh the
    result page, so this must never double-charge or double-verify.

    On a verified success, this also converts the order's stock
    *reservation* into a real deduction via `finalize_paid_order` -
    previously this step was missing here, which meant `reserved_stock`
    was incremented at order-creation time but never released/converted
    after a successful payment, silently corrupting inventory numbers
    over time. Fixed by locking + finalizing the order in the same
    transaction as the status flip, so a crash here rolls back atomically.
    """
    try:
        payment_transaction = (
            PaymentTransaction.objects.select_for_update()
            .select_related('order', 'gateway')
            .get(authority=authority, gateway__origin=gateway_origin)
        )
    except PaymentTransaction.DoesNotExist as exc:
        raise PaymentCreationError('No matching transaction was found for this authority.') from exc

    if payment_transaction.status != PaymentTransaction.Status.PENDING:
        return payment_transaction

    if gateway_status != 'OK':
        payment_transaction.status = PaymentTransaction.Status.FAILED
        payment_transaction.save(update_fields=['status', 'updated_at'])
        return payment_transaction

    adapter = get_adapter(payment_transaction.gateway)

    try:
        result = adapter.verify_payment(authority=authority, amount=payment_transaction.amount)
    except GatewayAdapterError as exc:
        payment_transaction.status = PaymentTransaction.Status.FAILED
        payment_transaction.raw_response = {'error': str(exc)}
        payment_transaction.save(update_fields=['status', 'raw_response', 'updated_at'])
        logger.warning('Payment verify failed for transaction %s: %s', payment_transaction.pk, exc)
        return payment_transaction

    payment_transaction.raw_response = result.raw_response
    payment_transaction.verified_at = timezone.now()

    if result.success:
        payment_transaction.status = PaymentTransaction.Status.SUCCESS
        payment_transaction.ref_id = result.ref_id
        payment_transaction.save(update_fields=['status', 'ref_id', 'raw_response', 'verified_at', 'updated_at'])

        # Lock the order row itself (not just the transaction) before
        # touching stock/status, since other flows (admin cancel, expiry
        # sweep) also mutate the same order under a row lock.
        order = Order.objects.select_for_update().get(pk=payment_transaction.order_id)
        finalize_paid_order(order)
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=['status', 'paid_at', 'updated_at'])
    else:
        payment_transaction.status = PaymentTransaction.Status.FAILED
        payment_transaction.save(update_fields=['status', 'raw_response', 'verified_at', 'updated_at'])

    return payment_transaction

"""
Business logic for turning a Cart into an Order and taking it through
payment. Kept out of views.py on purpose: views only handle HTTP concerns
(auth, request/response shapes), everything transactional/business-rule
related lives here so it's reusable (e.g. from an admin action or a
management command) and independently testable.

NOTE on imports: adjust these to match your actual app layout. This file
assumes Cart/Order/OrderItem/Gateway/PaymentTransaction are importable
from `apps.orders.models` (i.e. a models/ package with an __init__.py
that re-exports them, as is typical for the cart_model.py / order_model.py
/ gateway_model.py / transaction_model.py files reviewed earlier).
"""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Gateway, Order, OrderItem, PaymentTransaction
from apps.payments.adapters.base import GatewayAdapterError
from apps.payments.adapters.registery import get_adapter

logger = logging.getLogger(__name__)

ORDER_PAYMENT_TIMEOUT_MINUTES = getattr(settings, 'ORDER_PAYMENT_TIMEOUT_MINUTES', 15)
PENDING_TRANSACTION_TIMEOUT_MINUTES = getattr(settings, 'PENDING_TRANSACTION_TIMEOUT_MINUTES', 20)


class OrderCreationError(Exception):
    """Raised when a Cart can't be turned into an Order (empty, already converted, out of stock, ...)."""


class PaymentCreationError(Exception):
    """Raised when a payment attempt can't be started (order not payable, gateway failure, ...)."""


@transaction.atomic
def create_order_from_cart(*, cart, user, address, customer_note: str = '') -> Order:
    """
    Turn an active Cart into a payable Order.

    - `select_for_update()`s the cart's items so two concurrent "place
      order" requests (double-click, duplicate tab) can't both succeed.
    - Re-validates stock at order-creation time — prices/stock shown
      earlier in the cart view may be stale by checkout time.
    - Snapshots title/sku/options/unit_price onto each OrderItem, so the
      order keeps showing exactly what the buyer purchased even if the
      catalog changes later.
    - Marks the cart `converted_at` so it stops counting as "abandoned"
      and a fresh cart can be started for the user's next purchase.

    Raises OrderCreationError for any business-rule violation. Callers
    (views) are expected to turn that into a 400 response.
    """
    if cart.is_converted:
        raise OrderCreationError('این سبد قبلاً به سفارش تبدیل شده است.')

    items = list(cart.items.select_for_update().select_related('variant', 'variant__product'))
    if not items:
        raise OrderCreationError('سبد خرید خالی است.')

    subtotal_amount = 0
    order_items = []

    for item in items:
        variant = item.variant

        # TODO: replace with your real stock-check (e.g. a dedicated
        # inventory service). Left permissive (skip the check) if the
        # variant has no `stock` attribute, so this doesn't crash your
        # code out of the box — but you almost certainly want a real
        # check here before going to production.
        available_stock = getattr(variant, 'stock', None)
        if available_stock is not None and item.quantity > available_stock:
            raise OrderCreationError(f'موجودی «{variant.product.title}» کافی نیست.')

        unit_price = variant.price  # TODO: point at your real pricing (incl. any active discount)
        total_price = unit_price * item.quantity
        subtotal_amount += total_price

        order_items.append(OrderItem(
            variant=variant,
            title=variant.product.title,
            sku=variant.sku,
            options=getattr(variant, 'options', {}) or {},
            quantity=item.quantity,
            unit_price=unit_price,
            total_price=total_price,
        ))

    shipping_amount = 0  # TODO: plug in real shipping-cost calculation
    discount_amount = 0  # TODO: plug in coupon/discount calculation
    total_amount = subtotal_amount + shipping_amount - discount_amount

    order = Order.objects.create(
        user=user,
        address=address,
        cart=cart,
        subtotal_amount=subtotal_amount,
        shipping_amount=shipping_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        customer_note=customer_note,
        expires_at=timezone.now() + timezone.timedelta(minutes=ORDER_PAYMENT_TIMEOUT_MINUTES),
    )

    for order_item in order_items:
        order_item.order = order
    OrderItem.objects.bulk_create(order_items)

    cart.converted_at = timezone.now()
    cart.save(update_fields=['converted_at'])

    return order


@transaction.atomic
def create_payment_transaction(*, order: Order, gateway: Gateway, request) -> tuple[PaymentTransaction, str]:
    """
    Start (or resume) a payment attempt for `order` against `gateway`.

    - Rejects orders that are no longer payable (already paid / expired) —
      checked again here under a row lock, not just relying on whatever
      the caller believed.
    - If a PENDING transaction already exists for this order (this is also
      enforced at the DB level by `unique_pending_transaction_per_order`),
      it's reused instead of creating a duplicate: a user clicking "pay"
      twice gets redirected to the same payment session, not two of them.
    - Delegates the actual gateway call to `get_adapter(gateway)`, so this
      function has zero gateway-specific logic.

    Returns (transaction, redirect_url). Raises PaymentCreationError on
    any business-rule violation or gateway-side failure.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)

    if not order.is_payable:
        raise PaymentCreationError('این سفارش دیگر قابل پرداخت نیست (پرداخت‌شده یا منقضی شده است).')

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
            description=f'پرداخت سفارش {order.order_number}',
            mobile=getattr(order.user, 'phone', '') or '',
        )
    except GatewayAdapterError as exc:
        payment_transaction.status = PaymentTransaction.Status.FAILED
        payment_transaction.raw_response = {'error': str(exc)}
        payment_transaction.save(update_fields=['status', 'raw_response', 'updated_at'])
        logger.warning('Payment request failed for order %s: %s', order.order_number, exc)
        raise PaymentCreationError('اتصال به درگاه پرداخت ناموفق بود. لطفاً دوباره تلاش کنید.') from exc

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
    without calling the gateway's verify endpoint again — gateways
    sometimes hit the callback more than once, and users refresh the
    result page, so this must never double-charge or double-verify.
    """
    try:
        payment_transaction = PaymentTransaction.objects.select_for_update().select_related(
            'order', 'gateway'
        ).get(authority=authority, gateway__origin=gateway_origin)
    except PaymentTransaction.DoesNotExist as exc:
        raise PaymentCreationError('تراکنش معتبری برای این authority پیدا نشد.') from exc

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
        payment_transaction.save(
            update_fields=['status', 'ref_id', 'raw_response', 'verified_at', 'updated_at']
        )

        order = payment_transaction.order
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=['status', 'paid_at', 'updated_at'])
    else:
        payment_transaction.status = PaymentTransaction.Status.FAILED
        payment_transaction.save(update_fields=['status', 'raw_response', 'verified_at', 'updated_at'])

    return payment_transaction
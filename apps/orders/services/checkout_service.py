from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.db.models.functions import Greatest

from apps.catalog.models import ProductVariant
from apps.orders.models import Cart, Order, OrderItem

CHECKOUT_EXPIRE_MINUTES = getattr(settings, 'CHECKOUT_EXPIRE_MINUTES', 15)


class CheckoutError(Exception):
    """Base error for anything that should abort checkout with a 4xx."""


class EmptyCartError(CheckoutError):
    pass


class OutOfStockError(CheckoutError):
    def __init__(self, variant: ProductVariant, requested: int):
        self.variant = variant
        self.requested = requested
        super().__init__(
            f'Insufficient stock for variant {variant.sku}: requested {requested}, available {variant.available_stock}'
        )


@transaction.atomic
def create_order_from_cart(*, cart: Cart, address, customer_note: str = '') -> Order:
    """
    Turns a cart into a PENDING_PAYMENT order and reserves stock for it.

    Concurrency: locks the relevant ProductVariant rows with SELECT ... FOR
    UPDATE before checking availability, so two customers racing for the
    last unit can't both succeed. Must be called inside a transaction (the
    decorator handles that) - if OutOfStockError is raised everything,
    including the Order row already created, is rolled back.
    """
    cart_items = list(cart.items.select_related('variant').order_by('variant_id'))
    if not cart_items:
        raise EmptyCartError('Cart is empty')

    # Lock variants in a stable order (by id) to avoid deadlocks when two
    # checkouts share overlapping products.
    variant_ids = sorted({i.variant_id for i in cart_items})
    variants = {v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)}

    order = Order.objects.create(
        user=cart.user,
        address=address,
        customer_note=customer_note,
        expires_at=timezone.now() + timedelta(minutes=CHECKOUT_EXPIRE_MINUTES),
    )

    subtotal = 0
    order_items = []
    for cart_item in cart_items:
        variant = variants[cart_item.variant_id]

        if not variant.is_active or variant.available_stock < cart_item.quantity:
            raise OutOfStockError(variant, cart_item.quantity)

        total_price = variant.price * cart_item.quantity
        subtotal += total_price

        order_items.append(
            OrderItem(
                order=order,
                variant=variant,
                quantity=cart_item.quantity,
                unit_price=variant.price,
                total_price=total_price,
            )
        )

        variant.reserved_stock = models.F('reserved_stock') + cart_item.quantity
        variant.save(update_fields=['reserved_stock'])

    OrderItem.objects.bulk_create(order_items)

    order.subtotal_amount = subtotal
    order.total_amount = subtotal + order.shipping_amount - order.discount_amount
    order.save(update_fields=['subtotal_amount', 'total_amount'])

    cart.items.all().delete()

    return order


def _locked_order_variants(order: Order) -> tuple[dict[int, ProductVariant], dict[int, int]]:
    variant_ids = list(order.items.values_list('variant_id', flat=True))
    variants = {v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)}
    quantities = dict(order.items.values_list('variant_id', 'quantity'))
    return variants, quantities


@transaction.atomic
def release_reserved_stock(order: Order) -> None:
    variants, quantities = _locked_order_variants(order)
    for variant_id, variant in variants.items():
        ProductVariant.objects.filter(pk=variant_id).update(
            reserved_stock=Greatest(models.F('reserved_stock') - quantities[variant_id], 0)
        )


@transaction.atomic
def finalize_paid_order(order: Order) -> None:
    """Convert a reservation into a real stock deduction after payment succeeds."""
    variants, quantities = _locked_order_variants(order)
    for variant_id, variant in variants.items():
        qty = quantities[variant_id]
        variant.stock = models.F('stock') - qty
        variant.reserved_stock = models.F('reserved_stock') - qty
        variant.save(update_fields=['stock', 'reserved_stock'])


def _claim_order(order_id: int, *, from_status: str, to_status: str) -> Order | None:
    updated = Order.objects.filter(pk=order_id, status=from_status).update(status=to_status)
    if not updated:
        return None
    return Order.objects.select_related().get(pk=order_id)


@transaction.atomic
def expire_order(order_id: int) -> None:
    order = _claim_order(
        order_id,
        from_status=Order.Status.PENDING_PAYMENT,
        to_status=Order.Status.EXPIRED,
    )
    if order is None:
        return
    release_reserved_stock(order)


@transaction.atomic
def cancel_order(order_id: int) -> None:
    order = _claim_order(
        order_id,
        from_status=Order.Status.PENDING_PAYMENT,
        to_status=Order.Status.CANCELLED,
    )
    if order is None:
        return
    release_reserved_stock(order)


@transaction.atomic
def mark_order_paid_manually(order_id: int) -> None:
    """
    Admin override for offline/bank-transfer confirmations - skips gateway
    verification entirely. Use sparingly and only when payment has been
    confirmed through some other channel; there's no PaymentTransaction
    backing this, so it won't show up in gateway transaction history.
    """
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.Status.PENDING_PAYMENT:
        return
    finalize_paid_order(order)
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at'])


@transaction.atomic
def mark_order_refunded(order_id: int) -> None:
    """
    Flips status only. Deliberately does NOT restock automatically (returned
    items may need a quality check first) and does NOT call the gateway's
    refund API (amount/eligibility is a business decision) - both are left
    as explicit follow-up actions for the admin.
    """
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.Status.PAID:
        return
    order.status = Order.Status.REFUNDED
    order.save(update_fields=['status'])


def variant_allocation_cap(variant: ProductVariant, *, current_order_qty: int, order_is_paid: bool) -> int:
    """
    Max quantity of `variant` that can legally be assigned to a specific
    order line, given what that same order already holds.

    - Pending order: `current_order_qty` units are sitting in
      `reserved_stock` and can be freely reallocated back and forth, so the
      ceiling is `available_stock + current_order_qty`.
    - Paid order: `current_order_qty` units were already deducted from real
      `stock` and handed over - they're not part of any reservable pool
      anymore, so *increasing* this line can only draw from genuinely free
      `available_stock` (no `+ current_order_qty` term).
    """
    if order_is_paid:
        return variant.available_stock
    return variant.available_stock + current_order_qty


@transaction.atomic
def apply_order_item_delta(*, variant_id: int, delta: int, order_is_paid: bool) -> None:
    """
    Adjusts stock bookkeeping for a single line-item change made through the
    admin (add/increase/decrease/remove). `delta` is signed: positive means
    more of the variant is now allocated to the order, negative means less.

    Pending order -> the change lives entirely in `reserved_stock`.
    Paid order -> the order already consumed real `stock`, so the change is
    applied directly to `stock` instead (increasing a paid order's item
    really does take physical stock; decreasing gives it back).
    """
    if delta == 0:
        return
    variant = ProductVariant.objects.select_for_update().get(pk=variant_id)
    if order_is_paid:
        variant.stock = models.F('stock') - delta
        variant.save(update_fields=['stock'])
    else:
        variant.reserved_stock = models.F('reserved_stock') + delta
        variant.save(update_fields=['reserved_stock'])


@transaction.atomic
def recalculate_order_totals(order_id: int) -> None:
    order = Order.objects.select_for_update().get(pk=order_id)
    subtotal = sum(item.total_price for item in order.items.all())
    order.subtotal_amount = subtotal
    order.total_amount = subtotal + order.shipping_amount - order.discount_amount
    order.save(update_fields=['subtotal_amount', 'total_amount'])

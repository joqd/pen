import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Cart, Order
from apps.orders.services.checkout_service import expire_order

logger = logging.getLogger(__name__)

# Configurable via settings; sensible defaults if not set there.
GUEST_CART_STALE_DAYS = getattr(settings, 'GUEST_CART_STALE_DAYS', 30)
ORDER_RETENTION_DAYS = getattr(settings, 'ORDER_RETENTION_DAYS', 90)

# Delete in small batches instead of one giant DELETE, so cleanup tasks
# don't hold a long-lived lock on a large table.
CLEANUP_BATCH_SIZE = 500


def _delete_in_batches(queryset, batch_size=CLEANUP_BATCH_SIZE):
    """Deletes a queryset in batches. Returns the total number of rows deleted."""
    model = queryset.model
    total_deleted = 0
    while True:
        ids = list(queryset.values_list('pk', flat=True)[:batch_size])
        if not ids:
            break
        with transaction.atomic():
            model.objects.filter(pk__in=ids).delete()
        total_deleted += len(ids)
        logger.info(
            'cleanup: deleted %s %s rows (running total %s)',
            len(ids),
            model.__name__,
            total_deleted,
        )
    return total_deleted


@shared_task(bind=True, max_retries=3)
def expire_pending_orders(self):
    """
    Run every 1-2 minutes via Celery beat. Picks orders whose checkout
    window has passed and releases their reserved stock. `expire_order`
    re-locks and re-checks status per-order, so this is safe even if a
    payment callback resolves an order in the same instant.
    """
    stale_ids = list(
        Order.objects.filter(
            status=Order.Status.PENDING_PAYMENT,
            expires_at__lt=timezone.now(),
        ).values_list('id', flat=True)
    )
    for order_id in stale_ids:
        expire_order(order_id)
    return {'expired': len(stale_ids)}


@shared_task(bind=True, max_retries=3)
def cleanup_stale_guest_carts(self):
    """
    Run daily via Celery beat. Deletes guest (anonymous) carts that haven't
    been touched in GUEST_CART_STALE_DAYS days.

    Safe by design:
    - Only targets user__isnull=True (guest carts). Logged-in users' carts
      are OneToOne with the user and are never touched here.
    - A cart never holds a stock reservation itself (the reservation lives
      on the Order/ProductVariant level once checkout happens), so deleting
      a stale cart has zero impact on stock or Order integrity.
    - Order.cart is on_delete=SET_NULL, so even a cart that was already
      converted into an order can be safely deleted - the resulting Order
      just keeps cart_id=NULL; its own data is untouched.
    - CartItem is expected to be on_delete=CASCADE from Cart, so items go
      with it automatically.
    """
    cutoff = timezone.now() - timezone.timedelta(days=GUEST_CART_STALE_DAYS)
    stale_carts = Cart.objects.filter(user__isnull=True, updated_at__lt=cutoff)

    deleted = _delete_in_batches(stale_carts)
    logger.info('cleanup_stale_guest_carts: deleted %s carts older than %s', deleted, cutoff)
    return {'deleted_guest_carts': deleted, 'cutoff': cutoff.isoformat()}


@shared_task(bind=True, max_retries=3)
def purge_old_orders(self):
    """
    Run daily via Celery beat. Permanently deletes orders that have sat in a
    terminal "dead" state (EXPIRED / CANCELLED) for longer than
    ORDER_RETENTION_DAYS.

    Deliberately conservative:
    - Only EXPIRED and CANCELLED - never PAID/REFUNDED/PROCESSING. Paid
      orders are financial records and must be kept (or archived, never
      hard-deleted), regardless of age.
    - Uses `updated_at` (not `created_at`/`expires_at`) as the retention
      clock, since that reflects when the order actually reached its
      terminal state.
    - Reserved stock is NOT touched here. By the time an order is
      EXPIRED/CANCELLED, expire_order()/cancel_order() has already released
      its reservation via release_reserved_stock(). This task only removes
      rows that are otherwise inert.
    - Never touches PENDING_PAYMENT orders, even old ones - that's
      expire_pending_orders' job. If an order is stuck in PENDING_PAYMENT
      past its expiry, that's a sign expire_pending_orders failed for it,
      not something this task should paper over by deleting it.
    - OrderItem cascades with the Order (on_delete=CASCADE), so no orphaned
      line items are left behind.
    """
    cutoff = timezone.now() - timezone.timedelta(days=ORDER_RETENTION_DAYS)
    dead_orders = Order.objects.filter(
        status__in=[Order.Status.EXPIRED, Order.Status.CANCELLED],
        updated_at__lt=cutoff,
    )

    deleted = _delete_in_batches(dead_orders)
    logger.info('purge_old_orders: deleted %s orders older than %s', deleted, cutoff)
    return {'deleted_orders': deleted, 'cutoff': cutoff.isoformat()}

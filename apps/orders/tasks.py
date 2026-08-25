from celery import shared_task
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.services.checkout_service import expire_order


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

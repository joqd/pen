from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Order
from .services.checkout_service import release_reserved_stock


@receiver(pre_delete, sender=Order)
def release_stock_on_order_delete(sender, instance: Order, **kwargs):
    updated = Order.objects.filter(
        pk=instance.pk, status=Order.Status.PENDING_PAYMENT
    ).update(status=Order.Status.CANCELLED)
    if updated:
        release_reserved_stock(instance)
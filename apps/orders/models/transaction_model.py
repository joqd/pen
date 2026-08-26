from django.db import models
from django.utils.translation import gettext_lazy as _

from .gateway_model import Gateway
from .order_model import Order


class PaymentTransaction(models.Model):
    """
    A single payment attempt against a Gateway for an Order.

    Renamed from `Checkout`: "checkout" describes the user-facing process
    (cart -> address -> payment), not a payment record, and an Order can
    have several of these (a failed attempt, then a successful retry), so
    keeping it as its own auditable model is clearer than overloading the
    Order itself.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', _('pending')
        SUCCESS = 'success', _('success')
        FAILED = 'failed', _('failed')

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions', verbose_name=_('order'))
    gateway = models.ForeignKey(
        Gateway, on_delete=models.PROTECT, related_name='transactions', verbose_name=_('gateway')
    )

    # Returned by the gateway when the payment session is created (e.g.
    # Zarinpal's "Authority"); used to build the redirect URL and to match
    # the callback request back to this attempt.
    authority = models.CharField(_('authority'), max_length=100, blank=True, db_index=True)
    # Returned by the gateway ONLY after a successful, verified payment
    # (e.g. Zarinpal's "RefID"). Keep separate from `authority` since the
    # two exist at different stages of the flow and both need to be looked
    # up independently.
    ref_id = models.CharField(_('reference id'), max_length=100, blank=True, db_index=True)

    amount = models.PositiveBigIntegerField(_('amount'))
    status = models.CharField(_('status'), max_length=20, choices=Status.choices, default=Status.PENDING)

    raw_response = models.JSONField(_('raw response'), default=dict, blank=True)

    expires_at = models.DateTimeField(_('expires at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    verified_at = models.DateTimeField(_('verified at'), null=True, blank=True)

    class Meta:
        verbose_name = _('payment transaction')
        verbose_name_plural = _('payment transactions')
        ordering = ['-id']
        constraints = [
            # A given authority code must resolve to exactly one transaction.
            # NOTE: the original model referenced a field called `authority`
            # here while the actual field was named `reference` — that's a
            # bug (Django would fail its system checks on this constraint).
            # Fixed by adding the `authority` field above to match.
            models.UniqueConstraint(
                fields=['gateway', 'authority'],
                condition=models.Q(authority__gt=''),
                name='unique_gateway_authority',
            ),
            # Prevent two simultaneously "pending" attempts on the same
            # order — otherwise a user could open two payment tabs/retries
            # and risk paying twice before either callback lands.
            models.UniqueConstraint(
                fields=['order'],
                condition=models.Q(status='pending'),
                name='unique_pending_transaction_per_order',
            ),
        ]

    def __str__(self):
        return f'{self.order.order_number} - {self.get_status_display()}'

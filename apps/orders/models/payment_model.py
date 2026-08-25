from django.db import models
from django.utils.translation import gettext_lazy as _

from .order_model import Order


class PaymentTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('pending')
        SUCCESS = 'success', _('success')
        FAILED = 'failed', _('failed')

    class Gateway(models.TextChoices):
        AQAYEPARDAKHT = 'aqayepardakht', _('aqayepardakht')

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions', verbose_name=_('order'))
    gateway = models.CharField(_('gateway'), max_length=20, choices=Gateway.choices, default=Gateway.AQAYEPARDAKHT)

    authority = models.CharField(_('gateway reference'), max_length=100, blank=True, db_index=True)
    amount = models.PositiveIntegerField(_('amount'))
    status = models.CharField(_('status'), max_length=20, choices=Status.choices, default=Status.PENDING)

    raw_response = models.JSONField(_('raw response'), default=dict, blank=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    verified_at = models.DateTimeField(_('verified at'), null=True, blank=True)

    class Meta:
        verbose_name = _('payment transaction')
        verbose_name_plural = _('payment transactions')
        ordering = ['-id']
        constraints = [
            # a given authority code must resolve to exactly one transaction
            models.UniqueConstraint(
                fields=['gateway', 'authority'],
                condition=models.Q(authority__gt=''),
                name='unique_gateway_authority',
            ),
        ]

    def __str__(self):
        return f'{self.order.order_number} - {self.get_status_display()}'

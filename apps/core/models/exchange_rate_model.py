from django.db import models
from django.utils.translation import gettext_lazy as _


class ExchangeRate(models.Model):
    currency = models.CharField(_('currency'), max_length=3, default='USD')
    rate = models.DecimalField(_('rate'), max_digits=20, decimal_places=0)
    source = models.CharField(_('source'), max_length=50, blank=True)
    fetched_at = models.DateTimeField(
        _('fetched at'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('exchange rate')
        verbose_name_plural = _('exchange rates')
        ordering = ['-fetched_at']
        indexes = [models.Index(fields=['currency', '-fetched_at'])]

    def __str__(self):
        return f'{self.currency}: {self.rate:,} IRR'

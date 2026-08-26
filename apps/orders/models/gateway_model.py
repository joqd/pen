from django.db import models
from django.utils.translation import gettext_lazy as _


class Gateway(models.Model):
    class Origin(models.TextChoices):
        AQAYEPARDAKHT = 'aqayepardakht', _('aqayepardakht')
        ZARINPAL = 'zarinpal', _('zarinpal')

    title = models.CharField(_('title'), max_length=100, unique=True)
    badge = models.TextField(_('badge'), blank=True)

    # NOTE: this stores gateway secrets (merchant id / api key) as plain
    # JSON. In production, encrypt this at rest (e.g. django-encrypted-
    # model-fields) or keep secrets out of the DB entirely and reference
    # them from environment/secret-manager by gateway id.
    credentials = models.JSONField(_('credentials'), default=dict, blank=True)
    origin = models.CharField(_('origin'), max_length=50, choices=Origin.choices)
    description = models.TextField(_('description'), blank=True, null=True)

    min_amount = models.PositiveBigIntegerField(_('minimum amount'), null=True, blank=True)
    max_amount = models.PositiveBigIntegerField(_('maximum amount'), null=True, blank=True)

    priority = models.PositiveIntegerField(_('priority'), default=0)
    is_active = models.BooleanField(_('is active'), default=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = _('gateway')
        verbose_name_plural = _('gateways')
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(max_amount__isnull=True)
                    | models.Q(min_amount__isnull=True)
                    | models.Q(max_amount__gte=models.F('min_amount'))
                ),
                name='gateway_max_amount_gte_min_amount',
            ),
        ]

    def __str__(self):
        return self.title

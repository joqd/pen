from django.db import models
from django.utils.translation import gettext_lazy as _


class Gateway(models.Model):
    class Origin(models.TextChoices):
        AQAYEPARDAKHT = 'aqayepardakht', _('aqayepardakht')
        ZARINPAL = 'zarinpal', _('zarinpal')

    title = models.CharField(_('title'), max_length=100, unique=True)
    badge = models.TextField(_('badge'))
    credentials = models.JSONField(_('credentials'), default=dict, blank=True)
    origin = models.CharField(_('origin'), max_length=50, choices=Origin.choices)
    description = models.TextField(blank=True, null=True)
    priority = models.PositiveIntegerField(_('priority'), default=0)
    is_active = models.BooleanField(_('is active'), default=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = _('gateway')
        verbose_name_plural = _('gateways')

    def __str__(self):
        return self.title
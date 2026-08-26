from django.db import models
from django.utils.translation import gettext_lazy as _


class FooterBadge(models.Model):
    title = models.CharField(_('title'), max_length=100, unique=True)
    html = models.TextField(_('html'))
    priority = models.PositiveIntegerField(_('priority'), default=0)
    is_active = models.BooleanField(_('is active'), default=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = _('footer badge')
        verbose_name_plural = _('footer badges')

    def __str__(self):
        return self.title

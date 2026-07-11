from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Product


class CustomerGallery(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='customer_gallery', verbose_name=_('product'), null=True, blank=True)
    image = models.ImageField(_('image'), upload_to='gallery/customers/')
    customer_name = models.CharField(_('customer name'), max_length=100, blank=True)
    caption = models.CharField(_('caption'), max_length=255, blank=True)
    is_active = models.BooleanField(_('is active'), default=True)
    sort_order = models.PositiveIntegerField(_('sort order'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        ordering = ['sort_order', '-id']
        verbose_name = _('customer gallery image')
        verbose_name_plural = _('customer gallery images')

    def __str__(self):
        return self.customer_name or str(self.product) or self.pk
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .product_model import Product


class Audio(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='audio',
        verbose_name=_('product'),
    )
    audio = models.FileField(
        _('audio'),
        upload_to='products/audio/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])],
    )
    title = models.CharField(_('title'), max_length=100)
    cover = models.ImageField(_('cover'), upload_to='products/cover')
    artist = models.CharField(_('artist'), max_length=100)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('audio')
        verbose_name_plural = _('audios')

    def __str__(self):
        return self.title

from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(_('slug'), max_length=255, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='children',
        blank=True,
        null=True,
        verbose_name=_('parent'),
    )
    short_description = models.CharField(_('short description'), max_length=320, blank=True)
    description = models.TextField(_('description'), blank=True)
    image = models.ImageField(_('image'), upload_to='catalog/category/', blank=True, null=True)
    image_dark = models.ImageField(_('image dark'), upload_to='catalog/category/', blank=True, null=True)
    is_active = models.BooleanField(_('is active'), default=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        ordering = ['title']
        indexes = [
            models.Index(fields=['parent', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(parent=models.F('id')),
                name='catalog_category_parent_not_self',
            )
        ]

    def __str__(self) -> str:
        return self.title

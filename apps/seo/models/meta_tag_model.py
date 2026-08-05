from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class MetaTag(models.Model):
    class TwitterCard(models.TextChoices):
        SUMMARY = 'summary', _('Summary')
        SUMMARY_LARGE_IMAGE = 'summary_large_image', _('Summary Large Image')

    product = models.OneToOneField(
        'catalog.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='meta_tag',
        verbose_name=_('product'),
    )
    category = models.OneToOneField(
        'catalog.Category',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='meta_tag',
        verbose_name=_('category'),
    )
    collection = models.OneToOneField(
        'catalog.Collection',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='meta_tag',
        verbose_name=_('collection'),
    )
    post = models.OneToOneField(
        'blog.Post',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='meta_tag',
        verbose_name=_('post'),
    )

    # Basic tags
    title = models.CharField(_('title'), max_length=60)
    description = models.CharField(_('description'), max_length=160)
    canonical_url = models.URLField(_('canonical url'), blank=True)
    is_indexable = models.BooleanField(_('is indexable'), default=True)

    # Open Graph / Twitter
    og_title = models.CharField(_('og title'), max_length=95, blank=True)
    og_description = models.CharField(_('og description'), max_length=200, blank=True)
    og_image = models.ImageField(_('og image'), upload_to='seo/og/', blank=True, null=True)
    twitter_card = models.CharField(
        max_length=32,
        choices=TwitterCard.choices,
        default=TwitterCard.SUMMARY_LARGE_IMAGE,
        verbose_name=_('twitter card'),
    )

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('metatag')
        verbose_name_plural = _('metatags')
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(product__isnull=False, category__isnull=True, collection__isnull=True, post__isnull=True)
                    | models.Q(product__isnull=True, category__isnull=False, collection__isnull=True, post__isnull=True)
                    | models.Q(product__isnull=True, category__isnull=True, collection__isnull=False, post__isnull=True)
                    | models.Q(product__isnull=True, category__isnull=True, collection__isnull=True, post__isnull=False)
                ),
                name='metatag_exactly_one_target',
            )
        ]

    def clean(self):
        targets = [self.product_id, self.category_id, self.collection_id, self.post_id]
        filled = [t for t in targets if t is not None]
        if len(filled) != 1:
            raise ValidationError(_('Exactly one of the product/category/collection/post fields must be set.'))

    def save(self, *args, **kwargs):
        self.full_clean()

        if not self.og_title:
            self.og_title = self.title
        if not self.og_description:
            self.og_description = self.description
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.product or self.category or self.collection or self.post
        return target if target else self.pk

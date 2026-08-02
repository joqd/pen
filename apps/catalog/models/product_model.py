from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .category_model import Category
from .collection_model import Collection
from .tag_model import Tag


class ProductStatus(models.TextChoices):
    DRAFT = 'draft', 'پیش‌نویس'
    ACTIVE = 'active', 'فعال'
    ARCHIVED = 'archived', 'آرشیو'


class Product(models.Model):
    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(_('slug'), max_length=255, unique=True)
    short_description = models.CharField(_('short description'), max_length=320)
    description = models.TextField(_('description'), blank=True)
    audio = models.FileField(
        _('audio'),
        upload_to='products/audio/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])],
    )

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, related_name='products', blank=True, null=True, verbose_name=_('category')
    )
    collections = models.ManyToManyField(Collection, related_name='products', blank=True, verbose_name=_('collection'))
    tags = models.ManyToManyField(Tag, related_name='products', blank=True, verbose_name=_('collection'))

    status = models.CharField(_('status'), max_length=20, choices=ProductStatus.choices, default=ProductStatus.DRAFT)
    published_at = models.DateTimeField(_('published at'), blank=True, null=True)
    featured = models.BooleanField(_('featured'), default=False)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')
        ordering = ['-published_at', '-id']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['featured', 'status']),
        ]

    def __str__(self) -> str:
        return self.title


class ProductImage(models.Model):
    class MediaKind(models.TextChoices):
        GALLERY = 'gallery', 'گالری'
        SIZE_CHART = 'size_chart', 'جدول سایز'
        FABRIC_GUIDE = 'fabric_guide', 'راهنمای پارچه'
        DESIGN = 'design', 'طرح'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name=_('product'))
    image = models.ImageField(_('image'), upload_to='catalog/products/%Y/%m/')
    media_kind = models.CharField(_('media kind'), max_length=20, choices=MediaKind.choices, default=MediaKind.GALLERY)
    caption = models.CharField(_('caption'), max_length=255, blank=True)
    alt_text = models.CharField(_('alt text'), max_length=255)
    is_primary = models.BooleanField(_('is primary'), default=False)
    sort_order = models.PositiveIntegerField(_('sort order'), default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('product image')
        verbose_name_plural = _('product images')
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['product', 'sort_order']),
            models.Index(fields=['product', 'media_kind']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_primary=True),
                name='catalog_productimage_single_primary',
            )
        ]

    def __str__(self) -> str:
        return f'{self.product.title} image {self.id}'


class ProductSize(models.Model):
    name = models.CharField(_('name'), max_length=20)
    sort_order = models.PositiveIntegerField(_('sort order'), default=0)
    is_active = models.BooleanField(_('is_active'), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('product size')
        verbose_name_plural = _('product sizes')
        ordering = ['sort_order', 'id']


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE, verbose_name=_('product'))
    sku = models.CharField(_('sku'), max_length=64, unique=True)
    size = models.ForeignKey(ProductSize, on_delete=models.PROTECT, verbose_name=_('size'))
    price = models.PositiveIntegerField(_('price'))
    compare_price = models.PositiveIntegerField(_('compare price'), blank=True, null=True)
    stock = models.PositiveIntegerField(_('stock'), default=0)
    reserved_stock = models.PositiveIntegerField(_('reserved stock'), default=0)
    is_active = models.BooleanField(_('is_active'), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.product.title} - {self.sku}'

    @property
    def available_stock(self):
        return self.stock - self.reserved_stock

    class Meta:
        verbose_name = _('product variant')
        verbose_name_plural = _('product variants')
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['product', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(compare_price__isnull=True) | models.Q(compare_price__gte=models.F('price'))),
                name='catalog_variant_compare_price_gte_price',
            ),
            models.UniqueConstraint(fields=['product', 'size'], name='catalog_variant_unique_size'),
        ]

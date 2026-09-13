import logging
import secrets
from decimal import ROUND_HALF_UP, Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import ExchangeRate

from .category_model import Category
from .collection_model import Collection

logger = logging.getLogger(__name__)


class ProductStatus(models.TextChoices):
    DRAFT = 'draft', 'پیش‌نویس'
    ACTIVE = 'active', 'فعال'
    ARCHIVED = 'archived', 'آرشیو'


class Product(models.Model):
    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(_('slug'), max_length=255, unique=True)
    short_description = models.CharField(_('short description'), max_length=320)
    description = models.TextField(_('description'), blank=True)

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, related_name='products', blank=True, null=True, verbose_name=_('category')
    )
    collections = models.ManyToManyField(Collection, related_name='products', blank=True, verbose_name=_('collection'))

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
    name = models.CharField(_('name'), max_length=100)
    label = models.CharField(_('label'), max_length=25)
    is_active = models.BooleanField(_('is_active'), default=True)

    def __str__(self):
        return self.name or self.label

    class Meta:
        verbose_name = _('product size')
        verbose_name_plural = _('product sizes')
        ordering = ['id']


class SizeAttribute(models.Model):
    size = models.ForeignKey(
        ProductSize,
        related_name='attributes',
        on_delete=models.CASCADE,
        verbose_name=_('size'),
    )
    key = models.CharField(_('key'), max_length=50)
    value = models.CharField(_('value'), max_length=50)
    sort_order = models.PositiveIntegerField(_('sort order'), default=0)

    def __str__(self):
        return f'{self.key}: {self.value}'

    class Meta:
        verbose_name = _('size attribute')
        verbose_name_plural = _('size attributes')
        ordering = ['sort_order', 'id']


class ProductVariant(models.Model):
    # How much local-currency price is rounded to (e.g. nearest 10,000 Toman).
    PRICE_ROUNDING_STEP = Decimal('10000')

    # Cache key/TTL for the latest USD rate, to avoid one extra query per
    # variant when serializing lists of products.
    _USD_RATE_CACHE_KEY = 'catalog:latest_usd_exchange_rate'
    _USD_RATE_CACHE_TTL = 300  # seconds

    product = models.ForeignKey('Product', related_name='variants', on_delete=models.CASCADE, verbose_name=_('product'))
    sku = models.CharField(_('sku'), max_length=64, unique=True)
    size = models.ForeignKey('ProductSize', on_delete=models.PROTECT, verbose_name=_('size'))

    # Set manually in the admin panel. These are the source of truth now;
    # `price` / `compare_price` below are derived from them and are never
    # stored directly. Keeping both in USD means their ratio (the discount)
    # stays stable regardless of exchange-rate fluctuations, and it lets us
    # validate one against the other without needing a rate at all.
    base_price_usd = models.DecimalField(
        _('base price (USD)'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text=_(
            'Price in USD. The displayed price is computed automatically from this value and the latest exchange rate.'
        ),
    )
    compare_price_usd = models.DecimalField(
        _('compare price (USD)'),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_('Original/strikethrough price in USD. Leave empty if this variant has no discount.'),
    )

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

    @property
    def price(self):
        """
        Computed local-currency price = base_price_usd * latest USD rate,
        rounded to the nearest PRICE_ROUNDING_STEP.

        Returns None if no exchange rate is available yet, so callers
        (serializers, templates, admin) can decide how to handle that
        instead of silently showing 0 or a wrong price.
        """
        return self._compute_local_price(self.base_price_usd)

    @property
    def compare_price(self):
        """
        Computed local-currency compare price, same rules as `price`.
        Returns None when there's no discount set (compare_price_usd is
        empty) or when no exchange rate is available yet.
        """
        if self.compare_price_usd is None:
            return None
        return self._compute_local_price(self.compare_price_usd)

    def _compute_local_price(self, usd_value):
        price = self.compute_price_from_usd(usd_value)
        if price is None:
            logger.error(
                'No USD exchange rate available; cannot compute price for variant id=%s sku=%s',
                self.id,
                self.sku,
            )
        return price

    @classmethod
    def compute_price_from_usd(cls, usd_value):
        """
        Public helper to convert a raw USD amount (e.g. an aggregated
        Min/Max of base_price_usd across variants) into the rounded local
        price, using the same rate/rounding rules as `price`/`compare_price`.
        Returns None if usd_value is None or no exchange rate is available.
        Doesn't require a ProductVariant instance.
        """
        if usd_value is None:
            return None

        rate = cls._get_latest_usd_rate()
        if rate is None:
            return None

        raw_price = Decimal(usd_value) * Decimal(rate)
        return cls._round_to_step(raw_price, cls.PRICE_ROUNDING_STEP)

    @classmethod
    def _get_latest_usd_rate(cls):
        rate = cache.get(cls._USD_RATE_CACHE_KEY)
        if rate is not None:
            return rate

        rate = (
            ExchangeRate.objects.filter(currency='USD').order_by('-fetched_at').values_list('rate', flat=True).first()
        )
        if rate is not None:
            cache.set(cls._USD_RATE_CACHE_KEY, rate, cls._USD_RATE_CACHE_TTL)
        return rate

    @staticmethod
    def _round_to_step(value, step):
        return int((Decimal(value) / step).to_integral_value(rounding=ROUND_HALF_UP) * step)

    SKU_LENGTH = 8
    SKU_MAX_ATTEMPTS = 10

    def generate_sku(self):
        for __ in range(self.SKU_MAX_ATTEMPTS):
            candidate = f'{secrets.randbelow(10**self.SKU_LENGTH):0{self.SKU_LENGTH}d}'
            if not ProductVariant.objects.filter(sku=candidate).exists():
                return candidate

        raise RuntimeError(
            f'Could not generate a unique SKU for product_id={self.product_id} '
            f'size_id={self.size_id} after {self.SKU_MAX_ATTEMPTS} attempts.'
        )

    def clean(self):
        super().clean()
        # Both values are now in USD, so we can validate them directly
        # against each other without needing an exchange rate at all.
        # This is also enforced at the DB level (see the CheckConstraint
        # in Meta) -- this just gives a friendlier error in the admin.
        if (
            self.compare_price_usd is not None
            and self.base_price_usd is not None
            and self.compare_price_usd < self.base_price_usd
        ):
            raise ValidationError(
                {
                    'compare_price_usd': _('Compare price (USD) must be greater than or equal to base price (USD).'),
                }
            )

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('product variant')
        verbose_name_plural = _('product variants')
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['product', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['product', 'size'], name='catalog_variant_unique_size'),
            # Both sides are real USD columns now, so unlike `price` before,
            # this can (and should) still be enforced at the DB level.
            models.CheckConstraint(
                condition=(
                    models.Q(compare_price_usd__isnull=True)
                    | models.Q(compare_price_usd__gte=models.F('base_price_usd'))
                ),
                name='catalog_variant_compare_price_usd_gte_base_price_usd',
            ),
        ]

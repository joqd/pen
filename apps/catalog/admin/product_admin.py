from django.contrib import admin
from django.contrib.admin import display
from django.db.models import Count, Max, Min, Prefetch, Sum
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline

from apps.seo.admin import ProductMetaTagInline

from ..models import (
    Audio,
    Product,
    ProductImage,
    ProductSize,
    ProductVariant,
    SizeAttribute,
)


def _format_computed_price(value):
    """
    Shared formatting for read-only computed-price columns/fields across
    the Product and ProductVariant admins. Returns an em dash when the
    price can't be computed yet (e.g. no USD exchange rate fetched yet).
    """
    if value is None:
        return '—'
    return f'{value:,}'


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 0

    fields = (
        # "preview",
        'image',
        'media_kind',
        'is_primary',
        'sort_order',
        'caption',
        'alt_text',
    )

    readonly_fields = ('preview',)
    ordering = ('sort_order', 'id')

    @display(description='Preview')
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return '—'

        return format_html(
            '<img src="{}" style="width:72px;height:72px;object-fit:cover;border-radius:10px;" />',
            obj.image.url,
        )


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 0

    # `base_price_usd` / `compare_price_usd` are what's actually editable
    # here. `computed_price` / `computed_compare_price` are read-only
    # previews of what the customer will see, using the latest exchange
    # rate, so whoever edits this inline doesn't have to do the math.
    fields = (
        'size',
        'sku',
        'base_price_usd',
        'compare_price_usd',
        'computed_price',
        'computed_compare_price',
        'stock',
        'is_active',
    )

    readonly_fields = ('sku', 'computed_price', 'computed_compare_price')
    autocomplete_fields = ('size',)

    @display(description=_('price'))
    def computed_price(self, obj):
        if obj is None or obj.pk is None:
            return '—'
        return _format_computed_price(obj.price)

    @display(description=_('compare price'))
    def computed_compare_price(self, obj):
        if obj is None or obj.pk is None:
            return '—'
        return _format_computed_price(obj.compare_price)


class AudioInline(TabularInline):
    model = Audio
    extra = 0
    max_num = 1
    can_delete = True


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    inlines = (
        ProductVariantInline,
        ProductImageInline,
        AudioInline,
        ProductMetaTagInline,
    )

    prepopulated_fields = {
        'slug': ('title',),
    }

    autocomplete_fields = (
        'category',
        'collections',
    )

    search_fields = (
        'title',
        'slug',
        'variants__sku',
    )

    list_filter = (
        'status',
        'featured',
        'category',
        'collections',
    )

    list_display = (
        'thumbnail',
        'title',
        'price_range',
        'variant_count',
        'total_stock',
        'featured',
        'status',
        'updated_at',
    )

    filter_horizontal = ('collections',)

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    fieldsets = (
        (
            _('General'),
            {
                'classes': ('tab',),
                'fields': (
                    'title',
                    'slug',
                    'category',
                    'collections',
                ),
            },
        ),
        (
            _('Content'),
            {
                'classes': ('tab',),
                'fields': (
                    'short_description',
                    'description',
                ),
            },
        ),
        (
            _('Publishing'),
            {
                'classes': ('tab',),
                'fields': (
                    'status',
                    'featured',
                    'published_at',
                ),
            },
        ),
        (
            _('Metadata'),
            {
                'classes': ('tab',),
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                'images',
                Prefetch('variants'),
            )
            .annotate(
                variants_count=Count('variants'),
                stock_sum=Sum('variants__stock'),
                # `price` is no longer a DB column (it's computed from
                # base_price_usd * exchange rate), so we can only
                # aggregate the raw USD values here. The conversion to
                # local currency happens once per row in price_range()
                # below, using the same (cached) rate for every row.
                min_base_price_usd=Min('variants__base_price_usd'),
                max_base_price_usd=Max('variants__base_price_usd'),
            )
        )

    @display(description=_('Image'))
    def thumbnail(self, obj):
        image = next(
            (img for img in obj.images.all() if img.is_primary),
            None,
        )

        if image is None:
            image = next(iter(obj.images.all()), None)

        if image is None:
            return '—'

        return format_html(
            '<img src="{}" style="width:54px;height:54px;object-fit:cover;border-radius:8px;" />',
            image.image.url,
        )

    @display(description=_('variants'), ordering='variants_count')
    def variant_count(self, obj):
        return obj.variants_count or 0

    @display(description=_('stock'), ordering='stock_sum')
    def total_stock(self, obj):
        return obj.stock_sum or 0

    @display(description=_('price'))
    def price_range(self, obj):
        if obj.min_base_price_usd is None:
            return '—'

        # Same USD amount -> same local price, so converting the min/max
        # USD values individually gives the correct min/max local range
        # (the rate is a positive scalar, it doesn't change ordering).
        min_price = ProductVariant.compute_price_from_usd(obj.min_base_price_usd)
        max_price = ProductVariant.compute_price_from_usd(obj.max_base_price_usd)

        if min_price is None or max_price is None:
            # base_price_usd values exist, but no exchange rate is
            # available yet to convert them.
            return '—'

        if min_price == max_price:
            return _format_computed_price(min_price)

        return f'{_format_computed_price(min_price)} → {_format_computed_price(max_price)}'


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    autocomplete_fields = (
        'product',
        'size',
    )

    list_select_related = (
        'product',
        'size',
    )

    search_fields = (
        'sku',
        'product__title',
    )

    list_filter = (
        'size',
        'is_active',
    )

    # `price` is a computed property now (not a DB column), so it can no
    # longer be sorted/filtered on directly. It still works fine as a
    # read-only list_display column via the method below.
    list_display = (
        'sku',
        'product',
        'size',
        'display_price',
        'stock',
        'is_active',
        'updated_at',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'display_price',
        'display_compare_price',
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'product',
                    'size',
                    'sku',
                    'base_price_usd',
                    'compare_price_usd',
                    'display_price',
                    'display_compare_price',
                    'stock',
                    'is_active',
                ),
            },
        ),
        (
            'Metadata',
            {
                'classes': ('tab',),
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )

    @display(description=_('price'))
    def display_price(self, obj):
        return _format_computed_price(obj.price)

    @display(description=_('compare price'))
    def display_compare_price(self, obj):
        return _format_computed_price(obj.compare_price)


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    autocomplete_fields = ('product',)

    list_select_related = ('product',)

    search_fields = (
        'product__title',
        'alt_text',
    )

    list_filter = (
        'media_kind',
        'is_primary',
    )

    list_display = (
        'preview',
        'product',
        'media_kind',
        'is_primary',
        'sort_order',
    )

    readonly_fields = (
        'preview',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'product',
                    'preview',
                    'image',
                    'media_kind',
                    'caption',
                    'alt_text',
                    'is_primary',
                    'sort_order',
                ),
            },
        ),
        (
            'Metadata',
            {
                'classes': ('tab',),
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )

    @display(description='Preview')
    def preview(self, obj):
        if not obj.image:
            return '—'

        return format_html(
            '<img src="{}" style="width:70px;height:70px;object-fit:cover;border-radius:10px;" />',
            obj.image.url,
        )


class SizeAttributeInline(TabularInline):
    model = SizeAttribute
    extra = 1
    fields = ('key', 'value', 'sort_order')


@admin.register(ProductSize)
class ProductSizeAdmin(ModelAdmin):
    inlines = [SizeAttributeInline]
    list_display = ('name', 'label', 'is_active')
    search_fields = ('name', 'label')

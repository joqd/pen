from django.contrib import admin
from django.contrib.admin import display
from django.db.models import Count, Max, Min, Prefetch, Sum
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline

from ..models import (
    Product,
    ProductImage,
    ProductSize,
    ProductVariant,
)


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

    fields = (
        'size',
        'sku',
        'price',
        'compare_price',
        'stock',
        'is_active',
    )

    autocomplete_fields = ('size',)


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    inlines = (
        ProductImageInline,
        ProductVariantInline,
    )

    prepopulated_fields = {
        'slug': ('title',),
    }

    autocomplete_fields = (
        'category',
        'collections',
        'tags',
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
        'tags',
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

    filter_horizontal = (
        'collections',
        'tags',
    )

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
                    'tags',
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
                min_price=Min('variants__price'),
                max_price=Max('variants__price'),
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
        if obj.min_price is None:
            return '—'

        if obj.min_price == obj.max_price:
            return f'{obj.min_price:,}'

        return f'{obj.min_price:,} → {obj.max_price:,}'


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

    list_display = (
        'sku',
        'product',
        'size',
        'price',
        'stock',
        'is_active',
        'updated_at',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'product',
                    'size',
                    'sku',
                    'price',
                    'compare_price',
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


@admin.register(ProductSize)
class ProductSizeAdmin(ModelAdmin):
    list_display = (
        'name',
        'sort_order',
        'is_active',
    )

    list_editable = (
        'sort_order',
        'is_active',
    )

    search_fields = ('name',)

    ordering = (
        'sort_order',
        'id',
    )

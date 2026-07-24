from django.contrib import admin
from django.contrib.admin import display
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import CustomerGallery


@admin.register(CustomerGallery)
class CustomerGalleryAdmin(ModelAdmin):
    autocomplete_fields = ('product',)

    list_select_related = ('product',)

    search_fields = (
        'customer_name',
        'caption',
        'product__title',
        'product__slug',
    )

    list_filter = (
        'is_active',
        'product',
        'created_at',
    )

    list_display = (
        'preview',
        'product',
        'customer_name',
        'score',
        'is_active',
        'sort_order',
        'created_at',
    )

    list_editable = (
        'is_active',
        'sort_order',
    )

    readonly_fields = (
        'preview',
        'created_at',
    )

    fieldsets = (
        (
            _('image'),
            {
                'classes': ('tab',),
                'fields': (
                    'product',
                    'image',
                ),
            },
        ),
        (
            _('information'),
            {
                'classes': ('tab',),
                'fields': (
                    'customer_name',
                    'caption',
                    'score',
                    'is_active',
                    'sort_order',
                ),
            },
        ),
        (
            _('Metadata'),
            {
                'classes': ('tab',),
                'fields': ('created_at',),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')

    @display(description=_('image'))
    def preview(self, obj):
        if not obj.image:
            return '—'

        return format_html(
            '<img src="{}" style="width:72px;height:72px;object-fit:cover;border-radius:12px;" />',
            obj.image.url,
        )

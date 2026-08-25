from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from ..models import FooterBadge, PaymentGateway


@admin.register(FooterBadge)
class FooterBadgeAdmin(ModelAdmin):
    list_display = (
        'title',
        'priority',
        'is_active',
        'created_at',
        'updated_at',
    )

    list_display_links = ('title',)
    list_filter = ('is_active',)
    search_fields = ('title',)
    ordering = ('-priority', '-created_at')

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (
            _('Badge'),
            {
                'fields': (
                    'title',
                    'html',
                ),
            },
        ),
        (
            _('Display'),
            {
                'fields': (
                    'priority',
                    'is_active',
                ),
            },
        ),
        (
            _('Metadata'),
            {
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(ModelAdmin):
    list_display = (
        'title',
        'priority',
        'is_active',
        'created_at',
        'updated_at',
    )

    list_display_links = ('title',)
    list_filter = ('is_active',)
    search_fields = ('title',)
    ordering = ('-priority', '-created_at')

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (
            _('payment gateway'),
            {
                'fields': (
                    'title',
                    'badge',
                    'merchant_id',
                    'base_url',
                ),
            },
        ),
        (
            _('Display'),
            {
                'fields': (
                    'priority',
                    'is_active',
                ),
            },
        ),
        (
            _('Metadata'),
            {
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )

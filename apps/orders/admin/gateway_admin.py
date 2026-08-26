from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from ..models import Gateway


@admin.register(Gateway)
class GatewayAdmin(ModelAdmin):
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
    ordering = ('-priority',)

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (
            _('gateway'),
            {
                'fields': (
                    'title',
                    'badge',
                    'credentials',
					'origin',
                    'description',
                ),
            },
        ),
        (
            _('display'),
            {
                'fields': (
                    'priority',
                    'is_active',
                ),
            },
        ),
        (
            _('metadata'),
            {
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )

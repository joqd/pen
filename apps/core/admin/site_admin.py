from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from ..models import FooterBadge


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
            _('badge'),
            {
                'fields': (
                    'title',
                    'html',
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

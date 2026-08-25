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

    search_fields = (
        'title',
        'html',
    )

    ordering = (
        '-priority',
        '-created_at',
    )

    list_editable = (
        'priority',
        'is_active',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

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
                'classes': ('collapse',),
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )

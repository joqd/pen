from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from ..models import ExchangeRate


@admin.register(ExchangeRate)
class ExchangeRateAdmin(ModelAdmin):
    list_display = (
        'currency',
        'rate_display',
        'source',
        'fetched_at',
    )
    list_display_links = ('currency',)
    list_filter = ('currency', 'source')
    search_fields = ('currency', 'source')
    ordering = ('-fetched_at',)
    readonly_fields = ('created_at',)
    list_per_page = 50

    @admin.display(description=_('rate'), ordering='rate')
    def rate_display(self, obj):
        return f'{obj.rate:,.0f} تومان'

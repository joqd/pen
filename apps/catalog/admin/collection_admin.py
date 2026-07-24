from django.contrib import admin
from django.contrib.admin import display
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from ..models import Collection


@admin.register(Collection)
class CollectionAdmin(ModelAdmin):
    search_fields = ['title', 'slug']
    list_display = ['thumbnail', 'title', 'slug', 'is_active', 'created_at']

    @display(description=_('Image'))
    def thumbnail(self, obj):
        if not obj.pk or not obj.image:
            return '—'

        return format_html(
            '<img src="{}" style="width:54px;height:54px;object-fit:cover;border-radius:10px;" />',
            obj.image.url,
        )

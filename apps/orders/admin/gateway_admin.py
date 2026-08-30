from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminTextareaWidget

from ..models import Gateway


class GatewayAdminForm(forms.ModelForm):
    class Meta:
        model = Gateway
        fields = '__all__'
        widgets = {
            'credentials': UnfoldAdminTextareaWidget(
                attrs={
                    'rows': 10,
                    'dir': 'ltr',
                    'spellcheck': 'false',
                }
            ),
        }


@admin.register(Gateway)
class GatewayAdmin(ModelAdmin):
    form = GatewayAdminForm

    list_display = (
        'id',
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
                    'origin',
                    'credentials',
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

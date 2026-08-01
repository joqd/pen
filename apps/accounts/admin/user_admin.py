from django.contrib import admin
from django.contrib.admin import display
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from ..models import User


@admin.register(User)
class CustomUserAdmin(ModelAdmin):
    ordering = ('-date_joined',)

    list_display = ('thumbnail', 'full_name', 'phone', 'date_joined')
    list_filter = ()
    search_fields = ('phone', 'full_name')
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = (
        (
            _('Account'),
            {
                'fields': (
                    'phone',
                    'full_name',
                    'avatar',
                )
            },
        ),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        (
            _('Important dates'),
            {
                'fields': (
                    'last_login',
                    'date_joined',
                )
            },
        ),
    )
    
    @display(description=_('Image'))
    def thumbnail(self, obj):
        if not obj.pk or not obj.avatar:
            return '—'

        return format_html(
            '<img src="{}" style="width:54px;height:54px;object-fit:cover;border-radius:10px;" />',
            obj.avatar.url,
        )

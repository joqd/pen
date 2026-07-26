from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from ..models import User


@admin.register(User)
class CustomUserAdmin(ModelAdmin):
    ordering = ('-date_joined',)

    list_display = ('full_name', 'phone', 'date_joined')
    list_display_links = ('phone',)
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
                    'password',
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

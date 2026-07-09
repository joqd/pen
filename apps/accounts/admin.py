from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import display
from unfold.admin import ModelAdmin

from .models import User, Address, Province, City


@admin.register(User)
class CustomUserAdmin(ModelAdmin):
    ordering = ("-date_joined",)

    list_display = ("phone", "date_joined")
    list_display_links = ("phone",)
    list_filter = ()
    search_fields = ("phone",)
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (
            _("Account"),
            {
                "fields": (
                    "phone",
                    "password",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )


@admin.register(Province)
class ProvinceAdmin(ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(City)
class CityAdmin(ModelAdmin):
    list_display = ("id", "name", "province")
    list_select_related = ("province",)

    search_fields = (
        "name",
        "province__name",
    )

    list_filter = (
        "province",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    autocomplete_fields = (
        "user",
        "province",
        "city",
    )

    list_select_related = (
        "user",
        "province",
        "city",
    )

    search_fields = (
        "title",
        "recipient_name",
        "phone",
        "postal_code",
        "address_line",
        "city__name",
        "province__name",
        "user__phone",
        "user__full_name",
    )

    list_filter = (
        "is_default",
        "province",
        "created_at",
    )

    list_display = (
        "id",
        "title",
        "user",
        "recipient_name",
        "phone",
        "location",
        "is_default",
        "updated_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            _("recipient"),
            {
                "classes": ("tab",),
                "fields": (
                    "user",
                    "title",
                    "recipient_name",
                    "phone",
                    "is_default",
                ),
            },
        ),
        (
            _("address"),
            {
                "classes": ("tab",),
                "fields": (
                    "province",
                    "city",
                    "postal_code",
                    "address_line",
                ),
            },
        ),
        (
            _("Metadata"),
            {
                "classes": ("tab",),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "user",
                "province",
                "city",
            )
        )

    @display(description=_("location"))
    def location(self, obj):
        return f"{obj.province.name} / {obj.city.name}"
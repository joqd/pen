from django.contrib import admin, messages
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from ..models import Review, ReviewStatus


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = (
        'id',
        'display_user',
        'display_product',
        'display_rating',
        'display_status',
        'created_at',
    )
    list_display_links = ('id', 'display_user')
    list_filter = ('status', 'rating', 'created_at')
    list_filter_submit = True

    search_fields = (
        'comment',
        'user__phone',
        'product__title',
        'product__slug',
    )
    search_help_text = _('Search by comment text, contact number, product slug or product title')

    autocomplete_fields = ('user', 'product')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 25

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (
            _('general'),
            {
                'fields': ('user', 'product'),
            },
        ),
        (
            _('review'),
            {
                'fields': ('rating', 'comment'),
            },
        ),
        (
            _('publishing'),
            {
                'fields': ('status',),
            },
        ),
        (
            _('datetime'),
            {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',),
            },
        ),
    )

    @display(description=_('user'))
    def display_user(self, obj: Review) -> str:
        return obj.user.full_name or obj.user.phone

    @display(description=_('product'))
    def display_product(self, obj: Review) -> str:
        return obj.product.title

    @display(description=_('rating'))
    def display_rating(self, obj: Review) -> str:
        return f'{"☆" * (5 - obj.rating)}{"★" * obj.rating}'

    @display(
        description=_('status'),
        label={
            ReviewStatus.PENDING: 'warning',
            ReviewStatus.APPROVED: 'success',
            ReviewStatus.REJECTED: 'danger',
        },
    )
    def display_status(self, obj: Review):
        return obj.status, obj.get_status_display()

    actions = ('approve_reviews', 'reject_reviews')

    @action(
        description=_('Approve selected comments'),
        icon='check_circle',
        variant='success',
    )
    def approve_reviews(self, request, queryset: QuerySet[Review]):
        updated = queryset.update(status=ReviewStatus.APPROVED)
        self.message_user(
            request,
            _('%(count)d comments were successfully approved.') % {'count': updated},
            level=messages.SUCCESS,
        )

    @action(
        description=_('Reject selected comments'),
        icon='cancel',
        variant='danger',
    )
    def reject_reviews(self, request, queryset: QuerySet[Review]):
        updated = queryset.update(status=ReviewStatus.REJECTED)
        self.message_user(
            request,
            _('%(count)d comments were rejected.') % {'count': updated},
            level=messages.WARNING,
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'product')

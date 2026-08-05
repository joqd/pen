from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold_markdown.widgets import MarkdownWidget

from apps.seo.admin import PostMetaTagInline

from ..models import Post, PostMedia

# ---------------------------------------------------------------------------
# Inline: media uploads attached to a post (images / video files)
# ---------------------------------------------------------------------------


class PostMediaInline(TabularInline):
    model = PostMedia
    extra = 1
    fields = ('file', 'media_preview', 'markdown_snippet')
    readonly_fields = ('media_preview', 'markdown_snippet')
    tab = True

    @display(description=_('preview'))
    def media_preview(self, obj):
        if not obj.file:
            return '-'
        if obj.is_video:
            return format_html(
                '<video src="{}" style="max-height:80px" controls></video>',
                obj.file.url,
            )
        return format_html(
            '<img src="{}" style="max-height:80px;border-radius:6px" />',
            obj.file.url,
        )

    @display(description=_('markdown-ready code'))
    def markdown_snippet(self, obj):
        if not obj.file:
            return '-'
        if obj.is_video:
            snippet = f'<video src="{obj.file.url}" controls></video>'
        else:
            snippet = f'![{obj.alt_text or ""}]({obj.file.url})'
        return format_html('<code>{}</code>', snippet)


# ---------------------------------------------------------------------------
# Post
# ---------------------------------------------------------------------------


@admin.register(Post)
class PostAdmin(ModelAdmin):
    # --- Unfold list view ---
    list_display = (
        'title',
        'author',
        'category',
        'status_badge',
        'published_at',
        'view_count',
    )
    list_filter = ('status', 'category', 'created_at')
    list_filter_submit = True
    search_fields = ('title', 'content', 'excerpt')
    autocomplete_fields = ('author', 'category')
    date_hierarchy = 'published_at'
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'view_count')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PostMediaInline, PostMetaTagInline]

    # Markdown editor only on the `content` field (not every TextField,
    # so excerpt / meta_description stay as plain admin textareas).
    formfield_overrides = {
        models.TextField: {'widget': MarkdownWidget},
    }

    fieldsets = (
        (
            _('main content'),
            {
                'fields': ('title', 'slug', 'author', 'category'),
            },
        ),
        (
            _('text'),
            {
                'fields': ('content', 'excerpt'),
            },
        ),
        (
            _('media'),
            {
                'fields': ('featured_image',),
            },
        ),
        (
            _('publishing'),
            {
                'fields': ('status', 'published_at', 'allow_comments'),
            },
        ),
        (
            _('seo'),
            {
                'fields': ('meta_title', 'meta_description'),
            },
        ),
        (
            _('system info'),
            {
                'fields': ('view_count', 'created_at', 'updated_at'),
            },
        ),
    )

    @display(
        description=_('status'),
        label={
            Post.Status.DRAFT: 'warning',
            Post.Status.PUBLISHED: 'success',
            Post.Status.ARCHIVED: 'info',
        },
    )
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    class Media:
        css = {'all': ('admin/css/custom.css',)}

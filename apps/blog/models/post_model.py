import bleach
import markdown as md
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Category

MARKDOWN_EXTENSIONS = [
    'extra',
    'codehilite',
    'toc',
    'sane_lists',
    'nl2br',
]

MARKDOWN_EXTENSION_CONFIGS = {
    'codehilite': {'guess_lang': False, 'css_class': 'highlight'},
}

ALLOWED_TAGS = [
    'p',
    'br',
    'hr',
    'span',
    'div',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'strong',
    'em',
    'b',
    'i',
    'u',
    'del',
    'code',
    'pre',
    'blockquote',
    'ul',
    'ol',
    'li',
    'a',
    'table',
    'thead',
    'tbody',
    'tr',
    'th',
    'td',
    'img',
]

ALLOWED_ATTRS = {
    'a': ['href', 'title', 'rel', 'id'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    '*': ['class', 'id', 'dir'],
}


def render_markdown(text: str) -> str:
    """Convert raw markdown text into sanitized HTML."""
    raw_html = md.markdown(
        text,
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
    return bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
    )


class PublishedPostManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Post.Status.PUBLISHED, published_at__lte=timezone.now())


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', _('draft')
        PUBLISHED = 'published', _('published')
        ARCHIVED = 'archived', _('archived')

    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(_('slug'), max_length=280, unique=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='posts',
        verbose_name=_('author'),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        verbose_name=_('category'),
    )

    excerpt = models.CharField(
        _('excerpt'),
        max_length=500,
        blank=True,
        help_text=_('short summary; if left blank, it will be automatically generated from the content.'),
    )
    content = models.TextField(_('content'), help_text=_('original text in Markdown format'))
    content_html = models.TextField(
        blank=True,
        editable=False,
        help_text=_('cache rendered HTML from content — do not edit manually.'),
        verbose_name=_('content html'),
    )

    featured = models.BooleanField(_('featured'), default=False)
    featured_image = models.ImageField(_('featured image'), upload_to='posts/%Y/%m/', blank=True, null=True)
    status = models.CharField(_('status'), max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    published_at = models.DateTimeField(_('published at'), null=True, blank=True, db_index=True)

    view_count = models.PositiveIntegerField(_('view count'), default=0)
    allow_comments = models.BooleanField(_('allow comments'), default=True)

    objects = models.Manager()  # default manager
    published = PublishedPostManager()  # .published.all()

    class Meta:
        verbose_name = _('post')
        verbose_name_plural = _('posts')
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['slug']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['slug'], name='unique_post_slug'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()

        # Auto-render markdown -> sanitized HTML on every save.
        self.content_html = render_markdown(self.content)

        if not self.excerpt:
            self.excerpt = self._auto_excerpt()

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.title, allow_unicode=True)
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            counter += 1
            slug = f'{base_slug}-{counter}'
        return slug

    def _auto_excerpt(self, length=200):
        plain = bleach.clean(self.content_html, tags=[], strip=True)
        plain = ' '.join(plain.split())
        return (plain[:length] + '…') if len(plain) > length else plain

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'slug': self.slug})

    @property
    def is_published(self):
        return (
            self.status == self.Status.PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )

    def increment_view_count(self):
        # avoid triggering save()/re-render on every hit
        Post.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)


def post_media_upload_path(instance, filename):
    return f'posts/{instance.post_id}/media/{filename}'


class PostMedia(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media', verbose_name=_('post'))
    file = models.FileField(_('file'), upload_to=post_media_upload_path)
    alt_text = models.CharField(_('alt text'), max_length=255, blank=True)
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)

    VIDEO_EXTENSIONS = ('.mp4', '.webm', '.mov', '.ogg')

    class Meta:
        verbose_name = _('post media')
        verbose_name_plural = _('post medias')
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.file.name

    @property
    def is_video(self):
        return self.file.name.lower().endswith(self.VIDEO_EXTENSIONS)

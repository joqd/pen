from django.db import models
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    title = models.CharField(_('title'), max_length=80, unique=True)
    slug = models.SlugField(_('slug'), max_length=120, unique=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = _('tag')
        verbose_name_plural = _('tags')

    def __str__(self) -> str:
        return self.title

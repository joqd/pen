from django.utils.translation import gettext_lazy as _
from unfold.admin import StackedInline

from .models import MetaTag


class BaseMetaTagInline(StackedInline):
    model = MetaTag
    extra = 0
    max_num = 1
    can_delete = True

    fieldsets = (
        (
            _('general'),
            {
                'fields': ('title', 'description', 'canonical_url', 'is_indexable'),
                'classes': ('tab',),
            },
        ),
        (
            _('open graph'),
            {
                'fields': ('og_title', 'og_description', 'og_image', 'twitter_card'),
                'classes': ('tab',),
            },
        ),
    )


class ProductMetaTagInline(BaseMetaTagInline):
    fk_name = 'product'


class CategoryMetaTagInline(BaseMetaTagInline):
    fk_name = 'category'


class CollectionMetaTagInline(BaseMetaTagInline):
    fk_name = 'collection'


class PostMetaTagInline(BaseMetaTagInline):
    fk_name = 'post'

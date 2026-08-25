from django.urls import path

from .views.site_schema_view import SiteSchemaView
from .views.sitemap_view import (
    CategorySitemapView,
    CollectionSitemapView,
    PostSitemapView,
    ProductSitemapView,
)

urlpatterns = [
    path('site-schema/', SiteSchemaView.as_view()),
    path('sitemap/posts/', PostSitemapView.as_view()),
    path('sitemap/products/', ProductSitemapView.as_view()),
    path('sitemap/collections/', CollectionSitemapView.as_view()),
    path('sitemap/categories/', CategorySitemapView.as_view()),
]

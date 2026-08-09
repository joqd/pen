from django.urls import path

from .views.site_schema_view import SiteSchemaView

urlpatterns = [
    path('site-schema/', SiteSchemaView.as_view(), name='site-schema'),
]

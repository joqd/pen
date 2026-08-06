from django.urls import path
from .views import SiteSchemaView

urlpatterns = [
    path("site-schema/", SiteSchemaView.as_view(), name="site-schema"),
]
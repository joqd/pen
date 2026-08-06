from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


@extend_schema(exclude=True)
class CustomSpectacularAPIView(SpectacularAPIView):
    pass


urlpatterns = [
    path('api/schema/', CustomSpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.catalog.urls')),
    path('api/', include('apps.orders.urls')),
    path('api/gallery/', include('apps.gallery.urls')),
    path('api/blog/', include('apps.blog.urls')),
    path('api/seo/', include('apps.seo.urls')),
]

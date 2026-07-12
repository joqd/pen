from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.utils import extend_schema


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
]
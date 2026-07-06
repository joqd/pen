from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
	path('api/zschema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
	path('api/auth/', include('apps.accounts.urls')),
	path('api/', include('apps.catalog.urls')),
]
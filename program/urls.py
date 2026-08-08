import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.api.urls')),
]

# Serve media locally only when S3 (Parspack) storage is not configured.
# When PARSPACK_BUCKET_NAME is set, media is served directly from the bucket
# and this route is unnecessary.
if not os.environ.get('PARSPACK_BUCKET_NAME'):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

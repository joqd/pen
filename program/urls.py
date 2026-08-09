import os

from django.contrib import admin
from django.urls import include, path, re_path

from program.core.media_serve import serve_media

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.api.urls')),
]

if not os.environ.get('PARSPACK_BUCKET_NAME'):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media),
    ]

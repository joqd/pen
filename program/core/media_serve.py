import mimetypes
import os
import stat

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseNotModified
from django.utils.http import http_date
from django.views.static import was_modified_since


def _safe_join(base, *paths):
    final_path = os.path.abspath(os.path.join(base, *paths))
    base = os.path.abspath(base)
    if not final_path.startswith(base + os.sep) and final_path != base:
        raise Http404('invalid path')
    return final_path


def serve_media(request, path):
    document_root = settings.MEDIA_ROOT
    full_path = _safe_join(document_root, path)

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404('file not found')

    statobj = os.stat(full_path)
    content_type, encoding = mimetypes.guess_type(full_path)
    content_type = content_type or 'application/octet-stream'

    if not was_modified_since(
        request.META.get('HTTP_IF_MODIFIED_SINCE'),
        statobj.st_mtime,
    ):
        return HttpResponseNotModified()

    etag = f'"{stat.S_IFMT(statobj.st_mode)}-{statobj.st_size}-{int(statobj.st_mtime)}"'
    if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
    if if_none_match and etag in if_none_match:
        return HttpResponseNotModified()

    response = FileResponse(open(full_path, 'rb'), content_type=content_type)

    if encoding:
        response['Content-Encoding'] = encoding

    response['Last-Modified'] = http_date(statobj.st_mtime)
    response['ETag'] = etag

    response['Cache-Control'] = 'public, max-age=0, must-revalidate'

    return response

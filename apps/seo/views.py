from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema

from apps.seo.schema_builders import OrganizationSchemaBuilder, WebsiteSchemaBuilder


@extend_schema(tags=['SEO'])
@method_decorator(cache_page(60 * 60 * 6), name="dispatch")
class SiteSchemaView(APIView):
    def get(self, request):
        return Response({
            "organization": OrganizationSchemaBuilder(request=request).to_json_ld(),
            "website": WebsiteSchemaBuilder(request=request).to_json_ld(),
        })
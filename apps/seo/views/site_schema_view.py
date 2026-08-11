from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.seo.views.schema_builders_view import OrganizationSchemaBuilder, WebsiteSchemaBuilder


@extend_schema(tags=['SEO'])
@method_decorator(cache_page(60 * 60 * 6), name='dispatch')
class SiteSchemaView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                'organization': OrganizationSchemaBuilder(request=request).to_json_ld(),
                'website': WebsiteSchemaBuilder(request=request).to_json_ld(),
            }
        )

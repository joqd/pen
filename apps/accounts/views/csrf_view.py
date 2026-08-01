from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from program.core.serializers import DetailResponseSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        summary='Set CSRF cookie',
        description='Ensures the csrftoken cookie is set on the client. Call once on app load.',
        responses={200: OpenApiResponse(response=DetailResponseSerializer)},
    )
    def get(self, request):
        get_token(request)

        response = DetailResponseSerializer(instance={'detail': 'CSRF cookie set.'})
        return Response(response.data, status=status.HTTP_200_OK)
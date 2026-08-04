from django.contrib.auth import logout
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from program.core.serializers import DetailResponseSerializer, ErrorResponseSerializer


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        summary='Logout current user',
        description='Invalidate the current session and log out the authenticated user.',
        responses={
            200: OpenApiResponse(
                response=DetailResponseSerializer,
                description='Logout successful.',
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Authentication required.',
            ),
        },
    )
    def post(self, request):
        logout(request)

        # response = DetailResponseSerializer(detail='logged out.')
        return Response(status=status.HTTP_200_OK)

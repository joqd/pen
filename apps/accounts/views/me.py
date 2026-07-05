from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.accounts.serializers import ErrorResponseSerializer, UserResponseSerializer


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        summary='Current authenticated user',
        description='Retrieve the profile of the currently authenticated user.',
        responses={
            200: OpenApiResponse(
                response=UserResponseSerializer,
                description='Authenticated user profile.',
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Authentication required.',
            ),
        },
    )
    def get(self, request):
        user = request.user

        d = {'id': user.id, 'phone': user.phone}
        return Response(d, status=status.HTTP_200_OK)
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from program.core.serializers import ErrorResponseSerializer

from ..serializers import UserResponseSerializer


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
        serializer = UserResponseSerializer(request.user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from program.core.serializers import ErrorResponseSerializer

from ..serializers import UserResponseSerializer
from ..serializers.user_serializer import UserUpdateSerializer


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
        serializer = UserResponseSerializer(
            request.user,
            context={'request': request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=['Auth'],
        summary='Update current user profile',
        description=("Update authenticated user's profile. Supported fields: full_name and avatar."),
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=UserResponseSerializer,
                description='Updated user profile.',
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Invalid data.',
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Authentication required.',
            ),
        },
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = UserResponseSerializer(
            request.user,
            context={
                'request': request,
            },
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

from django.conf import settings
from django.contrib.auth import get_user_model, login
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import LoginSerializer, VerifyOTPSerializer
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.sms_service import SMSService
from apps.accounts.throttles import (
    OTPPhoneRateThrottle,
    OTPRequestAnonRateThrottle,
    OTPResendPhoneRateThrottle,
    OTPThrottledMixin,
)
from apps.orders.services.cart_service import CartService

User = get_user_model()


class LoginAPIView(OTPThrottledMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPPhoneRateThrottle, OTPRequestAnonRateThrottle]

    @extend_schema(
        tags=['Auth'],
        summary='Request login OTP',
        description=(
            'Send a one-time password (OTP) to the specified phone number.\n\n'
            'The OTP is required to complete authentication using the '
            '`/auth/verify/` endpoint.\n\n'
            'Rate limited per phone number and per IP address.'
        ),
        request=LoginSerializer,
        examples=[
            OpenApiExample(
                name='Request Example',
                summary='Request OTP',
                value={
                    'phone': '9123456789',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        otp = OTPService.create_otp(phone)
        SMSService.send_otp(phone, otp.code)

        d = {
            'detail': 'OTP sent.',
            'code': otp.code if settings.DEBUG else None,
        }

        return Response(d, status=status.HTTP_200_OK)


class ResendOTPAPIView(OTPThrottledMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPResendPhoneRateThrottle, OTPRequestAnonRateThrottle]

    @extend_schema(
        tags=['Auth'],
        summary='Resend login OTP',
        description=(
            'Resend the one-time password (OTP) to the specified phone number.\n\n'
            'Subject to a stricter rate limit than the initial OTP request '
            'endpoint to prevent SMS abuse.'
        ),
        request=LoginSerializer,
        examples=[
            OpenApiExample(
                name='Request Example',
                summary='Resend OTP',
                value={
                    'phone': '9123456789',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        otp = OTPService.create_otp(phone)
        SMSService.send_otp(phone, otp.code)

        d = {
            'detail': 'OTP resent.',
            'code': otp.code if settings.DEBUG else None,
        }

        return Response(d, status=status.HTTP_200_OK)


class VerifyOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def _get_or_create_user(self, phone, full_name):
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={'full_name': full_name},
        )
        # کاربر موجودی که هنوز نام ندارد، با نام ارسالی تکمیل می‌شود
        if not created and full_name and not user.full_name:
            user.full_name = full_name
            user.save(update_fields=['full_name'])
        return user

    @extend_schema(
        tags=['Auth'],
        summary='Verify otp',
        description=(
            'Verify the one-time password (OTP).\n\n'
            'Optionally provide `full_name`. It is applied only when the user '
            'is new or does not have a name yet. Existing names are not changed here.'
        ),
        request=VerifyOTPSerializer,
        examples=[
            OpenApiExample(
                name='Request Example with name',
                summary='Verify OTP with name',
                value={'phone': '9123456789', 'code': 123456, 'full_name': 'علی رضایی'},
                request_only=True,
            ),
            OpenApiExample(
                name='Request Example without name',
                summary='Verify OTP',
                value={'phone': '9123456789', 'code': 123456},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']
        full_name = serializer.validated_data.get('full_name', '')

        # اول OTP بررسی می‌شود؛ قبل از آن هیچ تغییری روی کاربر انجام نمی‌شود
        otp = OTPService.verify(phone, code)
        if not otp:
            d = {'detail': 'invalid or expired code.'}
            return Response(d, status=status.HTTP_400_BAD_REQUEST)

        user = self._get_or_create_user(phone, full_name)

        login(request, user)

        # merging cart
        cart_token = request.COOKIES.get('cart_token')
        if cart_token:
            CartService.merge_cart_from_token(user=user, token=cart_token)

        d = {
            'id': user.id,
            'phone': user.phone,
            'full_name': user.full_name,
        }
        response = Response(d, status=status.HTTP_200_OK)
        response.delete_cookie('cart_token')

        return response

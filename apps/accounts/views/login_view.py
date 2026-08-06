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
    """
    ارسال مجدد OTP برای شماره‌ای که قبلاً یک درخواست OTP برایش ثبت شده.

    نرخ این Endpoint سخت‌گیرانه‌تر از LoginAPIView است (طبق اسکوپ
    `otp_resend` در تنظیمات Throttle) تا از ارسال پیاپی پیامک جلوگیری شود.
    """

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

    def _create_user_if_not_exist(self, phone):
        user, _ = User.objects.get_or_create(phone=phone)
        return user

    @extend_schema(
        tags=['Auth'],
        summary='Verify otp',
        description='Verify the one-time password (OTP).\n',
        request=VerifyOTPSerializer,
        examples=[
            OpenApiExample(
                name='Request Example',
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

        otp = OTPService.verify(phone, code)
        if not otp:
            d = {'detail': 'invalid or expired code.'}
            return Response(d, status=status.HTTP_400_BAD_REQUEST)

        user = self._create_user_if_not_exist(phone)

        login(request, user)

        # merging cart
        cart_token = request.COOKIES.get('cart_token')
        if cart_token:
            CartService.merge_cart_from_token(user=user, token=cart_token)

        d = {'id': user.id, 'phone': user.phone}
        response = Response(d, status=status.HTTP_200_OK)
        response.delete_cookie('cart_token')

        return response

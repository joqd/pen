from django.utils import timezone

from apps.accounts.models import OTPCode

from datetime import timedelta
import random


class OTPService:
    EXPIRY_MINUTES = 2

    @staticmethod
    def generate_code():
        return str(random.randint(10000, 99999))

    @classmethod
    def create_otp(cls, phone: str):
        code = cls.generate_code()

        otp = OTPCode.objects.create(
            phone=phone,
            code=code
        )

        return otp

    @staticmethod
    def is_valid(otp: OTPCode) -> bool:
        if not otp:
            return False

        expiry_time = otp.created_at + timedelta(minutes=2)
        return timezone.now() <= expiry_time

    @staticmethod
    def verify(phone: str, code: str):
        otp = (
            OTPCode.objects
            .filter(phone=phone, code=code)
            .order_by("-created_at")
            .first()
        )

        if not otp:
            return None

        if not OTPService.is_valid(otp):
            otp.delete()
            return None

        otp.delete()
        return otp
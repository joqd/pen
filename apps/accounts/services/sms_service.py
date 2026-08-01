from django.conf import settings
from sms_ir import SmsIr


class SMSService:
    @staticmethod
    def send_otp(phone: str, code: str) -> None:
        message = f'starboy.ir code: {code}'

        SMSService._send_sms(phone, message)

    @staticmethod
    def _send_sms(phone: str, message: str):
        client = SmsIr(settings.SMS_IR_API_KEY)

        return client.send_sms(
            number=phone,
            message=message,
            linenumber=settings.SMS_IR_LINE_NUMBER,
        )

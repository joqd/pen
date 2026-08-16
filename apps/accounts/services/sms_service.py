from django.conf import settings
from sms_ir import SmsIr


class SMSService:
    @staticmethod
    def send_otp(phone: str, code: str) -> None:
        parameters = [
            {
                'name': 'OTP',
                'value': code,
			}
		]
        SMSService._send_sms(phone, parameters)

    @staticmethod
    def _send_sms(phone: str, parameters: list):
        client = SmsIr(settings.SMS_IR_API_KEY)

        # if settings.DEBUG:
        #     print(f'new SMS sent to {phone}; message: {message}')

        return client.send_verify_code(
            number=phone,
            template_id=settings.SMS_TEMPLATE_ID,
            parameters=parameters,
        )

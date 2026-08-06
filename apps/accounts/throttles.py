from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class OTPPhoneRateThrottle(SimpleRateThrottle):
    scope = 'otp_request'

    def get_cache_key(self, request, view):
        phone = request.data.get('phone')
        if not phone:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': phone,
        }


class OTPResendPhoneRateThrottle(OTPPhoneRateThrottle):
    scope = 'otp_resend'


class OTPRequestAnonRateThrottle(AnonRateThrottle):
    scope = 'otp_request_ip'
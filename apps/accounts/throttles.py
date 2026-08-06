import math

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import Throttled
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


class OTPThrottledMixin:
    def throttled(self, request, wait):
        if wait is not None:
            wait_seconds = math.ceil(wait)
            detail = _('Too many requests. Please try again in %(wait)d seconds.') % {
                'wait': wait_seconds,
            }
        else:
            detail = _('Too many requests. Please try again later.')

        raise Throttled(wait=wait, detail=detail, code='throttled')
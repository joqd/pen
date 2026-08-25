import requests
from django.conf import settings
from django.urls import reverse

REQUEST_TIMEOUT = 10

VERIFY_ERROR_MESSAGES = {
    '-1': 'amount نمی‌تواند خالی باشد',
    '-2': 'کد پین درگاه نمی‌تواند خالی باشد',
    '-3': 'callback نمی‌تواند خالی باشد',
    '-4': 'amount باید عددی باشد',
    '-5': 'amount باید بین 1,000 تا 400,000,000 تومان باشد',
    '-6': 'کد پین درگاه اشتباه است',
    '-7': 'transid نمی‌تواند خالی باشد',
    '-8': 'تراکنش مورد نظر وجود ندارد',
    '-9': 'کد پین درگاه با درگاه تراکنش مطابقت ندارد',
    '-10': 'مبلغ با مبلغ تراکنش مطابقت ندارد',
    '-11': 'درگاه در انتظار تایید یا غیرفعال است',
    '0': 'پرداخت ناموفق بوده یا هنوز تایید نشده است',
}


class PaymentGatewayError(Exception):
    def __init__(self, message, payload=None):
        self.payload = payload
        super().__init__(message)


class AqayePardakhtGateway:
    """
    Wrapper around Aqaye Pardakht (panel.aqayepardakht.ir) API v2.

    Differences from Zarinpal-style gateways that matter elsewhere in the
    codebase:
    - the "tracking reference" is called `transid`, not `authority` (we
      still store it in PaymentTransaction.authority - it's a generic
      column, just holds whatever the active gateway calls its reference).
    - the callback the gateway hits is a POST with a single `transid`
      field and does NOT include a separate success/fail status - you must
      call /verify and read `code` to know the outcome.
    """

    CREATE_URL = 'https://panel.aqayepardakht.ir/api/v2/create'
    VERIFY_URL = 'https://panel.aqayepardakht.ir/api/v2/verify'
    STARTPAY_URL = 'https://panel.aqayepardakht.ir/startpay/{transid}'

    def __init__(self):
        self.pin = settings.AQAYEPARDAKHT_PIN
        self.callback_base_url = settings.CHECKOUT_CALLBACK_BASE_URL.rstrip('/')

    def _callback_url(self, order) -> str:
        path = reverse('orders:payment-callback')
        return f'{self.callback_base_url}{path}?order={order.token}'

    def request_payment(self, *, order, description: str = '') -> tuple[str, str]:
        """Returns (transid, redirect_url)."""
        payload = {
            'pin': self.pin,
            'amount': order.total_amount,
            'callback': self._callback_url(order),
            'invoice_id': order.order_number,
            'description': description or f'Order {order.order_number}',
        }
        # optional but recommended by the gateway when available
        mobile = getattr(order.user, 'phone', None)
        if mobile:
            payload['mobile'] = str(mobile)
        email = getattr(order.user, 'email', None)
        if email:
            payload['email'] = email

        try:
            response = requests.post(self.CREATE_URL, data=payload, timeout=REQUEST_TIMEOUT)
            result = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PaymentGatewayError('Gateway request failed') from exc

        if response.status_code != 200 or result.get('status') != 'success':
            raise PaymentGatewayError('Gateway rejected request', payload=result)

        transid = result['transid']
        return transid, self.STARTPAY_URL.format(transid=transid)

    def verify_payment(self, *, transid: str, amount: int) -> dict:
        payload = {
            'pin': self.pin,
            'amount': amount,
            'transid': transid,
        }
        try:
            response = requests.post(self.VERIFY_URL, data=payload, timeout=REQUEST_TIMEOUT)
            result = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PaymentGatewayError('Gateway verify failed') from exc

        code = str(result.get('code'))
        if response.status_code != 200 or code != '1':
            message = VERIFY_ERROR_MESSAGES.get(code, 'خطای نامشخص در تایید پرداخت')
            raise PaymentGatewayError(message, payload=result)

        return result

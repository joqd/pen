"""
Aghaye Pardakht (aqayepardakht.ir) gateway adapter.

Official API docs: https://aqayepardakht.ir/api/

Flow:
    1. POST /api/v2/create  -> {"status": "success", "transid": "..."}
    2. Redirect the buyer to /startpay/{transid}
       (or /startpay/sandbox/{transid} when using the "sandbox" pin)
    3. The gateway POSTs back to your callback URL with:
       transid, cardnumber, tracking_number, invoice_id, bank, status (1/0)
    4. POST /api/v2/verify -> {"status": "success", "code": "1"}
       code: "0" = not paid, "1" = paid, "2" = already verified
"""

from typing import Any

import requests

from .base import BaseGatewayAdapter, GatewayAdapterError, PaymentRequestResult, PaymentVerifyResult


class AqayePardakhtAdapter(BaseGatewayAdapter):
    BASE_URL = 'https://panel.aqayepardakht.ir'
    CREATE_URL = f'{BASE_URL}/api/v2/create'
    VERIFY_URL = f'{BASE_URL}/api/v2/verify'

    REQUEST_TIMEOUT = 15

    SUCCESS_STATUS = 'success'
    VERIFY_FAILED_CODE = '0'
    VERIFY_SUCCESS_CODE = '1'
    VERIFY_ALREADY_VERIFIED_CODE = '2'

    # Error codes documented at https://aqayepardakht.ir/api/
    ERROR_MESSAGES = {
        '-1': 'amount نمی‌تواند خالی باشد',
        '-2': 'کد پین درگاه نمی‌تواند خالی باشد',
        '-3': 'callback نمی‌تواند خالی باشد',
        '-4': 'amount باید عددی باشد',
        '-5': 'amount باید بین 100 تا 100,000,000 تومان باشد',
        '-6': 'کد پین درگاه اشتباه است',
        '-7': 'transid نمی‌تواند خالی باشد',
        '-8': 'تراکنش مورد نظر وجود ندارد',
        '-9': 'کد پین درگاه با درگاه تراکنش مطابقت ندارد',
        '-10': 'مبلغ با مبلغ تراکنش مطابقت ندارد',
        '-11': 'درگاه در انتظار تایید و یا غیرفعال است',
        '-12': 'امکان ارسال درخواست برای این پذیرنده وجود ندارد',
        '-13': 'شماره کارت باید 16 رقم چسبیده به هم باشد',
        '-14': 'درگاه بر روی سایت دیگری در حال استفاده است',
    }

    # -- credentials / environment -----------------------------------------
    @property
    def pin(self) -> str:
        pin = self.gateway.credentials.get('pin')
        if not pin:
            raise GatewayAdapterError(f'Gateway "{self.gateway}" has no pin configured.')
        return pin

    @property
    def is_sandbox(self) -> bool:
        # aqayepardakht's own convention: the literal pin value "sandbox"
        # puts the gateway in test mode; we also allow an explicit flag.
        return bool(self.gateway.credentials.get('sandbox', False)) or self.pin == 'sandbox'

    @property
    def startpay_url(self) -> str:
        """
        Base "start payment" URL to prepend a `transid` to, so callers
        (e.g. `services.py`, when resuming an existing pending transaction
        instead of calling `request_payment` again) can build the redirect
        URL themselves without duplicating the sandbox/live path logic.
        """
        path = '/startpay/sandbox/' if self.is_sandbox else '/startpay/'
        return f'{self.BASE_URL}{path}'

    # -- internal helpers ---------------------------------------------------
    def _error_message(self, code: Any) -> str:
        return self.ERROR_MESSAGES.get(str(code), 'خطای نامشخص از سمت آقای پرداخت')

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(url, data=payload, timeout=self.REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise GatewayAdapterError(f'Aqaye Pardakht request to {url} failed: {exc}') from exc

        try:
            return response.json()
        except ValueError as exc:
            raise GatewayAdapterError(
                f'Aqaye Pardakht returned a non-JSON response from {url} '
                f'(http_status={response.status_code}): {response.text[:200]!r}'
            ) from exc

    # -- public interface -----------------------------------------------

    def request_payment(
        self,
        *,
        amount: int,
        callback_url: str,
        description: str,
        mobile: str = '',
        email: str = '',
        card_number: str = '',
        invoice_id: str = '',
        callback_method: str = '',
    ) -> PaymentRequestResult:
        amount /= 10

        payload: dict[str, Any] = {
            'pin': self.pin,
            'amount': amount,
            'callback': callback_url,
        }
        if description:
            payload['description'] = description
        if mobile:
            payload['mobile'] = mobile
        if email:
            payload['email'] = email
        if card_number:
            payload['card_number'] = card_number
        if invoice_id:
            payload['invoice_id'] = invoice_id
        if callback_method:
            payload['callback_method'] = callback_method

        data = self._post(self.CREATE_URL, payload)

        if data.get('status') != self.SUCCESS_STATUS:
            raise GatewayAdapterError(
                f'Aqaye Pardakht payment request failed '
                f'(code={data.get("code")}: {self._error_message(data.get("code"))})'
            )

        transid = data.get('transid')
        if not transid:
            raise GatewayAdapterError(f'Aqaye Pardakht response missing "transid": {data}')

        return PaymentRequestResult(
            authority=str(transid),
            redirect_url=f'{self.startpay_url}{transid}',
            raw_response=data,
        )

    @classmethod
    def extract_callback_params(cls, request) -> tuple[str, str]:
        # Aqaye Pardakht POSTs back to your callback URL by default:
        #   transid, cardnumber, tracking_number, invoice_id, bank, status
        # where status is "1" (paid) / "0" (not paid) — NOT the same
        # vocabulary as Zarinpal's "OK"/"NOK". The rest of the codebase
        # (services.py) already speaks Zarinpal's "OK"/"NOK" convention for
        # its "skip verify on a known-failed callback" shortcut, so we
        # normalize to that same vocabulary here rather than leaking
        # Aqaye Pardakht's raw values up to gateway-agnostic code.
        #
        # If you passed callback_method='GET' in request_payment(), the
        # same fields arrive as query params instead of POST body, so we
        # fall back to query_params when the POST body is empty.
        data = getattr(request, 'data', None) or request.POST
        transid = data.get('transid', '') or request.query_params.get('transid', '')
        raw_status = data.get('status', '') or request.query_params.get('status', '')
        status = 'OK' if raw_status == '1' else 'NOK'
        return transid, status

    def verify_payment(self, *, authority: str, amount: int) -> PaymentVerifyResult:
        amount /= 10
        
        payload = {
            'pin': self.pin,
            'amount': amount,
            'transid': authority,
        }

        data = self._post(self.VERIFY_URL, payload)
        code = str(data.get('code', ''))

        if data.get('status') == self.SUCCESS_STATUS and code in (
            self.VERIFY_SUCCESS_CODE,
            self.VERIFY_ALREADY_VERIFIED_CODE,
        ):
            return PaymentVerifyResult(
                success=True,
                ref_id=str(authority),
                raw_response=data,
            )

        return PaymentVerifyResult(
            success=False,
            raw_response=data,
            error_code=code,
            error_message=self._error_message(code) if code else 'پرداخت تایید نشد.',
        )

"""
Zibal (zibal.ir) gateway adapter.

Official API docs: https://help.zibal.ir/IPG/API/

Flow:
    1. POST /v1/request  -> {"result": 100, "trackId": ..., "message": "success"}
    2. Redirect the buyer to /start/{trackId}
    3. Gateway redirects back (GET) with: trackId, success (1/0), status, orderId
    4. POST /v1/verify -> {"result": 100, "message": "success", "refNumber": ...}
       result: 100 = verified now, 201 = already verified, else = failure
"""

from typing import Any

import requests

from .base import BaseGatewayAdapter, GatewayAdapterError, PaymentRequestResult, PaymentVerifyResult


class ZibalAdapter(BaseGatewayAdapter):
    BASE_URL = 'https://gateway.zibal.ir'
    REQUEST_URL = f'{BASE_URL}/v1/request'
    VERIFY_URL = f'{BASE_URL}/v1/verify'
    START_URL = f'{BASE_URL}/start/'

    REQUEST_TIMEOUT = 15

    SUCCESS_RESULT = 100
    VERIFY_ALREADY_VERIFIED_RESULT = 201

    SANDBOX_MERCHANT = 'zibal'

    # https://help.zibal.ir/IPG/API/#result — shared between request/verify.
    ERROR_MESSAGES = {
        102: 'merchant یافت نشد',
        103: 'merchant غیرفعال است',
        104: 'merchant نامعتبر است',
        105: 'amount باید بزرگتر از 1,000 ریال باشد',
        106: 'callbackUrl نامعتبر است',
        113: 'amount مبلغ تراکنش بیشتر از سقف مجاز است',
        114: 'trackId نامعتبر است',
        201: 'قبلا تایید شده است',
        202: 'سفارش پرداخت نشده یا ناموفق بوده است',
        203: 'trackId نامعتبر است',
    }

    @property
    def merchant(self) -> str:
        merchant = self.gateway.credentials.get('merchant')
        if not merchant:
            raise GatewayAdapterError(f'Gateway "{self.gateway}" has no merchant configured.')
        return merchant

    @property
    def is_sandbox(self) -> bool:
        return bool(self.gateway.credentials.get('sandbox', False)) or self.merchant == self.SANDBOX_MERCHANT

    def _error_message(self, code: Any) -> str:
        try:
            code = int(code)
        except (TypeError, ValueError):
            return 'خطای نامشخص از سمت زیبال'
        return self.ERROR_MESSAGES.get(code, 'خطای نامشخص از سمت زیبال')

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(url, json=payload, timeout=self.REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise GatewayAdapterError(f'Zibal request to {url} failed: {exc}') from exc

        try:
            return response.json()
        except ValueError as exc:
            raise GatewayAdapterError(
                f'Zibal returned a non-JSON response from {url} '
                f'(http_status={response.status_code}): {response.text[:200]!r}'
            ) from exc

    def request_payment(
        self,
        *,
        amount: int,
        callback_url: str,
        description: str,
        mobile: str = '',
        email: str = '',
        order_id: str = '',
        card_number: str = '',
    ) -> PaymentRequestResult:
        # Zibal wants amount in Rials; convert before calling this method
        # if the rest of the codebase works in Tomans.
        payload: dict[str, Any] = {
            'merchant': self.merchant,
            'amount': amount,
            'callbackUrl': callback_url,
        }
        if description:
            payload['description'] = description
        if mobile:
            payload['mobile'] = mobile
        if email:
            payload['email'] = email
        if order_id:
            payload['orderId'] = order_id
        if card_number:
            payload['allowedCards'] = [card_number]

        data = self._post(self.REQUEST_URL, payload)

        if data.get('result') != self.SUCCESS_RESULT:
            raise GatewayAdapterError(
                f'Zibal payment request failed (result={data.get("result")}: {self._error_message(data.get("result"))})'
            )

        track_id = data.get('trackId')
        if not track_id:
            raise GatewayAdapterError(f'Zibal response missing "trackId": {data}')

        return PaymentRequestResult(
            authority=str(track_id),
            redirect_url=f'{self.START_URL}{track_id}',
            raw_response=data,
        )

    @classmethod
    def extract_callback_params(cls, request) -> tuple[str, str]:
        # GET callback: ?trackId=...&success=1|0&status=...&orderId=...
        track_id = request.query_params.get('trackId', '')
        success = request.query_params.get('success', '')
        status = 'OK' if success == '1' else 'NOK'
        return track_id, status

    def verify_payment(self, *, authority: str, amount: int) -> PaymentVerifyResult:
        payload = {
            'merchant': self.merchant,
            'trackId': authority,
        }

        data = self._post(self.VERIFY_URL, payload)
        result = data.get('result')

        if result in (self.SUCCESS_RESULT, self.VERIFY_ALREADY_VERIFIED_RESULT):
            # Defense in depth: confirm the paid amount actually matches.
            paid_amount = data.get('amount')
            if paid_amount is not None and int(paid_amount) != int(amount):
                return PaymentVerifyResult(
                    success=False,
                    raw_response=data,
                    error_code=str(result),
                    error_message='مبلغ پرداخت‌شده با مبلغ تراکنش مطابقت ندارد.',
                )

            return PaymentVerifyResult(
                success=True,
                ref_id=str(data.get('refNumber', authority)),
                raw_response=data,
            )

        return PaymentVerifyResult(
            success=False,
            raw_response=data,
            error_code=str(result or ''),
            error_message=self._error_message(result) if result else 'پرداخت تایید نشد.',
        )

"""
Zarinpal adapter (REST API v4).

Implemented against ZarinPal-Lab's official sample:
https://github.com/ZarinPal-Lab/Zarinpal-RestAPI-Sample-php

Request flow:
    POST {base}/request.json
    body: {merchant_id, amount, callback_url, description, metadata}
    -> data.code == 100  =>  redirect user to {startpay}/{data.authority}

Verify flow (called from our callback view after the user returns):
    POST {base}/verify.json
    body: {merchant_id, authority, amount}
    -> data.code == 100  =>  paid, data.ref_id is the settlement reference
    -> data.code == 101  =>  already verified earlier (treat as success —
       this happens if the callback fires more than once)
"""
from typing import Any

import requests
from django.conf import settings

from .base import BaseGatewayAdapter, GatewayAdapterError, PaymentRequestResult, PaymentVerifyResult


class ZarinpalAdapter(BaseGatewayAdapter):
    PRODUCTION_BASE_URL = 'https://api.zarinpal.com/pg/v4/payment'
    SANDBOX_BASE_URL = 'https://sandbox.zarinpal.com/pg/v4/payment'

    PRODUCTION_STARTPAY_URL = 'https://www.zarinpal.com/pg/StartPay/'
    SANDBOX_STARTPAY_URL = 'https://sandbox.zarinpal.com/pg/StartPay/'

    SUCCESS_CODE = 100
    ALREADY_VERIFIED_CODE = 101

    REQUEST_TIMEOUT_SECONDS = 15

    # -- credentials / environment -----------------------------------------
    #
    # Expected shape of Gateway.credentials for a Zarinpal gateway row:
    #   {"merchant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "sandbox": false}

    @property
    def merchant_id(self) -> str:
        merchant_id = self.gateway.credentials.get('merchant_id')
        if not merchant_id:
            raise GatewayAdapterError(f'Gateway "{self.gateway}" has no merchant_id configured.')
        return merchant_id

    @property
    def is_sandbox(self) -> bool:
        return bool(self.gateway.credentials.get('sandbox', getattr(settings, 'ZARINPAL_SANDBOX', False)))

    @property
    def base_url(self) -> str:
        return self.SANDBOX_BASE_URL if self.is_sandbox else self.PRODUCTION_BASE_URL

    @property
    def startpay_url(self) -> str:
        return self.SANDBOX_STARTPAY_URL if self.is_sandbox else self.PRODUCTION_STARTPAY_URL

    # -- HTTP plumbing --------------------------------------------------

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                f'{self.base_url}/{path}',
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'ZarinPal Rest Api v4 (django-adapter)',
                },
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise GatewayAdapterError(f'Network error while calling Zarinpal: {exc}') from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise GatewayAdapterError(
                f'Zarinpal returned a non-JSON response (HTTP {response.status_code}).'
            ) from exc

        return data

    # -- public interface -------------------------------------------------

    def request_payment(
        self,
        *,
        amount: int,
        callback_url: str,
        description: str,
        mobile: str = '',
        email: str = '',
    ) -> PaymentRequestResult:
        metadata = {}
        if mobile:
            metadata['mobile'] = mobile
        if email:
            metadata['email'] = email

        result = self._post('request.json', {
            'merchant_id': self.merchant_id,
            'amount': amount,
            'callback_url': callback_url,
            'description': description,
            'metadata': metadata,
        })

        data = result.get('data') or {}
        errors = result.get('errors') or {}

        if errors or data.get('code') != self.SUCCESS_CODE:
            raise GatewayAdapterError(
                f"Zarinpal payment request failed "
                f"(code={errors.get('code', data.get('code'))}, "
                f"message={errors.get('message', 'unknown error')})"
            )

        authority = data['authority']
        return PaymentRequestResult(
            authority=authority,
            redirect_url=f'{self.startpay_url}{authority}',
            raw_response=result,
        )

    def verify_payment(self, *, authority: str, amount: int) -> PaymentVerifyResult:
        result = self._post('verify.json', {
            'merchant_id': self.merchant_id,
            'authority': authority,
            'amount': amount,
        })

        data = result.get('data') or {}
        errors = result.get('errors') or {}
        code = data.get('code', errors.get('code'))

        if code in (self.SUCCESS_CODE, self.ALREADY_VERIFIED_CODE):
            return PaymentVerifyResult(
                success=True,
                ref_id=str(data.get('ref_id', '')),
                raw_response=result,
            )

        return PaymentVerifyResult(
            success=False,
            raw_response=result,
            error_code=str(code or ''),
            error_message=errors.get('message', ''),
        )
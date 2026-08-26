from functools import cached_property
from typing import Any

from django.conf import settings
from zarinpal import ZarinPal

from .base import BaseGatewayAdapter, GatewayAdapterError, PaymentRequestResult, PaymentVerifyResult


class Config:
    def __init__(self, sandbox, merchant_id, access_token):
        self.sandbox = sandbox
        self.merchant_id = merchant_id
        self.access_token = access_token


class ZarinpalAdapter(BaseGatewayAdapter):
    SUCCESS_CODE = 100
    ALREADY_VERIFIED_CODE = 101

    # -- credentials / environment -----------------------------------------
    @property
    def merchant_id(self) -> str:
        merchant_id = self.gateway.credentials.get('merchant_id')
        if not merchant_id:
            raise GatewayAdapterError(f'Gateway "{self.gateway}" has no merchant_id configured.')
        return merchant_id

    @property
    def access_token(self) -> str:
        access_token = self.gateway.credentials.get('access_token')
        if not access_token:
            raise GatewayAdapterError(f'Gateway "{self.gateway}" has no access_token configured.')
        return access_token

    @property
    def is_sandbox(self) -> bool:
        return bool(self.gateway.credentials.get('sandbox', getattr(settings, 'ZARINPAL_SANDBOX', False)))

    @cached_property
    def client(self) -> ZarinPal:
        config = Config(
            merchant_id=self.merchant_id,
            sandbox=self.is_sandbox,
            access_token=self.access_token,
        )
        return ZarinPal(config)

    # -- public interface -------------------------------------------------

    def request_payment(
        self,
        *,
        amount: int,
        callback_url: str,
        description: str,
        mobile: str = '',
        email: str = '',
        card_pan: list[str] | None = None,
        referrer_id: str = '',
    ) -> PaymentRequestResult:
        payload: dict[str, Any] = {
            'amount': amount,
            'callback_url': callback_url,
            'description': description,
        }
        if mobile:
            payload['mobile'] = mobile
        if email:
            payload['email'] = email
        if card_pan:
            payload['cardPan'] = card_pan
        if referrer_id:
            payload['referrer_id'] = referrer_id

        try:
            result = self.client.payments.create(payload)
        except Exception as exc:
            raise GatewayAdapterError(f'Zarinpal payment request failed: {exc}') from exc

        data = result.get('data') or {}
        errors = result.get('errors') or {}

        if errors or data.get('code') != self.SUCCESS_CODE:
            raise GatewayAdapterError(
                f'Zarinpal payment request failed '
                f'(code={errors.get("code", data.get("code"))}, '
                f'message={errors.get("message", "unknown error")})'
            )

        authority = data['authority']
        return PaymentRequestResult(
            authority=authority,
            redirect_url=self.client.payments.generate_payment_url(authority),
            raw_response=result,
        )

    def verify_payment(self, *, authority: str, amount: int) -> PaymentVerifyResult:
        try:
            result = self.client.verifications.verify(
                {
                    'amount': amount,
                    'authority': authority,
                }
            )
        except Exception as exc:
            raise GatewayAdapterError(f'Zarinpal payment verification failed: {exc}') from exc

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

    def inquire_payment(self, *, authority: str) -> dict[str, Any]:
        """Extra helper exposed by the new SDK: check a transaction's status
        without triggering verification (useful for support/debugging tools)."""
        try:
            return self.client.inquiries.inquire({'authority': authority})
        except Exception as exc:
            raise GatewayAdapterError(f'Zarinpal inquiry failed: {exc}') from exc

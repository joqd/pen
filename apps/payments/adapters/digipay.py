"""
Digipay (mydigipay.com) installment/BNPL gateway adapter.

Wraps the `digipay` ticket package (auth.py / digibase.py / tickets.py)
behind the same contract every other adapter implements.

Flow:
    1. POST /tickets/business  -> ticket created (see create_purchase_ticket)
    2. Redirect the buyer to the URL Digipay returns for that ticket.
    3. Digipay redirects back to the callback URL with the ticket's
       tracking code and a status.
    4. POST /tickets/{trackingCode}/verify -> confirms payment.
    5. POST /tickets/{trackingCode}/deliver -> confirms fulfilment. There's
       no slot for this in BaseGatewayAdapter's contract, so call it
       explicitly from order-fulfilment code once delivered:
       `get_adapter(gateway).ticket_service.deliver_ticket(tracking_code)`.

Auth is a Bearer token fetched via OAuth (see auth.DigipayAuthClient), using
client_id/client_secret/username/password from `gateway.credentials`.
`providerId` is not a gateway credential — it's a unique ID generated per
purchase (see `request_payment`'s `order_id` kwarg).

TODO(you): `redirectUrl` and `ticket` were confirmed from a real response.
Still unconfirmed: the callback param names in `extract_callback_params`,
and the exact shape (path vs. body/query) of the verify/deliver/reverse
calls in tickets.py — see the TODOs there.
"""

import uuid
from functools import cached_property
from typing import Any

from ..digipay import DigipayAuthClient, DigipayException, DigipayTicketService
from .base import BaseGatewayAdapter, GatewayAdapterError, PaymentRequestResult, PaymentVerifyResult


class DigipayAdapter(BaseGatewayAdapter):
    # `ticket` confirmed from a real response; others kept as fallbacks in
    # case the response shape varies across ticket types (wallet vs BNPL).
    TRACKING_CODE_KEYS = ('ticket', 'trackingCode', 'ticketId', 'id')
    REDIRECT_URL_KEYS = ('redirectUrl', 'redirectURL', 'ticketUrl', 'paymentUrl')

    @cached_property
    def auth_client(self) -> DigipayAuthClient:
        return DigipayAuthClient(self.gateway)

    @cached_property
    def ticket_service(self) -> DigipayTicketService:
        return DigipayTicketService(auth_client=self.auth_client)

    @staticmethod
    def _first_present(data: dict[str, Any], keys: tuple) -> Any:
        for key in keys:
            if data.get(key):
                return data[key]
        return None

    def request_payment(
        self,
        *,
        amount: int,
        callback_url: str,
        description: str,
        mobile: str = '',
        email: str = '',
        order_id: str = '',
    ) -> PaymentRequestResult:
        if not mobile:
            raise GatewayAdapterError('Digipay requires a mobile/cell number to open a ticket.')

        provider_id = order_id or uuid.uuid4().hex

        try:
            result = self.ticket_service.create_purchase_ticket(
                cell_number=mobile,
                amount=amount,
                provider_id=provider_id,
                callback_url=callback_url,
            )
        except DigipayException as exc:
            raise GatewayAdapterError(f'Digipay payment request failed: {exc}') from exc

        # A top-level "result" object carries a business-level status even
        # on HTTP 200 (status 0 = success).
        status = (result.get('result') or {}).get('status')
        if status is not None and status != 0:
            raise GatewayAdapterError(
                f'Digipay payment request failed '
                f'(status={status}: {(result.get("result") or {}).get("message", "unknown error")})'
            )

        tracking_code = self._first_present(result, self.TRACKING_CODE_KEYS)
        redirect_url = self._first_present(result, self.REDIRECT_URL_KEYS)

        if not tracking_code or not redirect_url:
            raise GatewayAdapterError(
                f'Digipay response is missing a tracking code / redirect URL under the '
                f'expected keys {self.TRACKING_CODE_KEYS + self.REDIRECT_URL_KEYS}. '
                f'Raw response: {result}'
            )

        return PaymentRequestResult(
            authority=str(tracking_code),
            redirect_url=redirect_url,
            raw_response=result,
        )

    def verify_payment(self, *, authority: str, amount: int, provider_id: str = '') -> PaymentVerifyResult:
        # Needs the same providerId used to create the ticket.
        if not provider_id:
            raise GatewayAdapterError(
                'Digipay verify_payment() requires provider_id — pass the same '
                'order_id that was used in request_payment() for this transaction.'
            )

        try:
            result = self.ticket_service.verify_ticket(tracking_code=authority, provider_id=provider_id)
        except DigipayException as exc:
            return PaymentVerifyResult(
                success=False,
                error_message=str(exc),
                error_code=str(getattr(exc, 'status_code', '') or ''),
                raw_response=getattr(exc, 'response_data', {}) or {},
            )

        return PaymentVerifyResult(
            success=True,
            ref_id=str(authority),
            raw_response=result,
        )

    @classmethod
    def extract_callback_params(cls, request) -> tuple[str, str]:
        # TODO(you): confirm Digipay's actual callback method/field names.
        # Assumed GET redirect with `trackingCode` + `status`.
        tracking_code = request.query_params.get('trackingCode', '')
        raw_status = request.query_params.get('status', '')
        status = 'OK' if raw_status.upper() in ('OK', '1', 'SUCCESS') else 'NOK'
        return tracking_code, status

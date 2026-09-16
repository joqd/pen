"""
Digipay (mydigipay.com) installment/BNPL gateway adapter.

Wraps the `digipay` ticket package (auth.py / digibase.py / tickets.py)
behind the same contract every other adapter implements, so
services.py / views.py never need to know Digipay's ticket-based flow is
different under the hood.

Flow:
    1. POST /tickets/business  -> ticket created (see create_purchase_ticket)
    2. Redirect the buyer to the URL Digipay returns for that ticket.
    3. Digipay redirects back to your callback URL with the ticket's
       tracking code and a status.
    4. POST /tickets/{trackingCode}/verify -> confirms payment.
    5. POST /tickets/{trackingCode}/deliver -> confirms fulfilment (Digipay's
       BNPL flow expects this once you've shipped/fulfilled the order —
       call it after verify_payment() succeeds and you've delivered;
       there's no slot for it in BaseGatewayAdapter's contract, so wire it
       up explicitly from your order-fulfilment code via
       `get_adapter(gateway).ticket_service.deliver_ticket(tracking_code)`).

Auth here is a Bearer token fetched via OAuth (see auth.DigipayAuthClient),
using client_id/client_secret/username/password read from
`gateway.credentials` — same place Zarinpal/Zibal/Aqaye Pardakht read
their own credentials from. `providerId`, on the other hand, is *not* a
gateway credential — it's a unique ID you generate per purchase (see
`request_payment`'s `order_id` kwarg below), so it's passed in per-call
instead, the same way Zibal takes `order_id` and Aqaye Pardakht takes
`invoice_id`.

TODO(you): `redirectUrl` and the ticket id (`ticket`) were confirmed from
a real response. Still unconfirmed: the callback param names in
`extract_callback_params`, and the exact shape (path vs. body/query) of
the verify/deliver/reverse calls in tickets.py — see the TODOs there.
"""

import uuid
from functools import cached_property
from typing import Any

# `digipay/` is a sibling package to this `adapters/` package (both live
# under `payments/`), so this goes up one level and back down — its
# __init__.py already exports these three.
from ..digipay import DigipayAuthClient, DigipayException, DigipayTicketService
from .base import BaseGatewayAdapter, GatewayAdapterError, PaymentRequestResult, PaymentVerifyResult


class DigipayAdapter(BaseGatewayAdapter):
    # Confirmed from a real create_purchase_ticket() response: the ticket
    # identifier comes back as `ticket` (not `trackingCode`/`ticketId` as
    # first guessed). Kept as a candidate list, `ticket` first, in case
    # Digipay's response shape varies across ticket types (wallet vs BNPL).
    TRACKING_CODE_KEYS = ('ticket', 'trackingCode', 'ticketId', 'id')
    REDIRECT_URL_KEYS = ('redirectUrl', 'redirectURL', 'ticketUrl', 'paymentUrl')

    # -- credentials / environment -----------------------------------------
    @cached_property
    def auth_client(self) -> DigipayAuthClient:
        # DigipayAuthClient reads client_id / client_secret / username /
        # password from `self.gateway.credentials` — see auth.py — so each
        # Gateway row can hold its own Digipay account, the same way
        # Zarinpal/Zibal/Aqaye Pardakht read their own credentials.
        return DigipayAuthClient(self.gateway)

    @cached_property
    def ticket_service(self) -> DigipayTicketService:
        return DigipayTicketService(auth_client=self.auth_client)

    # -- internal helpers ---------------------------------------------------
    @staticmethod
    def _first_present(data: dict[str, Any], keys: tuple) -> Any:
        for key in keys:
            if data.get(key):
                return data[key]
        return None

    # -- public interface -----------------------------------------------
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

        # `providerId` is your own unique identifier for this purchase, not
        # a gateway credential — pass your real order/purchase ID here
        # (e.g. order_id=str(order.pk)) so you can trace it back later.
        # Falls back to a random one so this still works if you don't have
        # one at hand yet.
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

        # Confirmed response shape: a top-level "result" object carries a
        # business-level status even on HTTP 200 (status 0 = success, per
        # a real response you shared: {'result': {'status': 0, ...}}).
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
        # Digipay's verify call needs the *same* providerId that was used
        # to create the ticket, alongside the tracking code — confirmed
        # against third-party Digipay SDKs, since it's not in the files
        # you sent me. Whatever calls verify_payment() for a Digipay
        # transaction needs to pass the order's own id back in here (the
        # same value given as `order_id` to request_payment), e.g.
        # `adapter.verify_payment(authority=..., amount=..., provider_id=str(order.pk))`.
        if not provider_id:
            raise GatewayAdapterError(
                'Digipay verify_payment() requires provider_id — pass the same '
                'order_id that was used in request_payment() for this transaction.'
            )

        try:
            result = self.ticket_service.verify_ticket(tracking_code=authority, provider_id=provider_id)
        except DigipayException as exc:
            # digibase.request() already turns any non-2xx response into
            # DigipayAPIError — there's no separate "already verified"
            # success code to special-case here the way Zarinpal/Zibal do,
            # because a call that returns at all *is* the success case.
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
        # TODO(you): confirm Digipay's actual callback method/field names —
        # not present in the files you sent me. Written here as a GET
        # redirect with `trackingCode` + `status`, normalized to the
        # shared 'OK'/'NOK' vocabulary the rest of the codebase already
        # uses for Zarinpal/Zibal/Aqaye Pardakht (see base.py).
        tracking_code = request.query_params.get('trackingCode', '')
        raw_status = request.query_params.get('status', '')
        status = 'OK' if raw_status.upper() in ('OK', '1', 'SUCCESS') else 'NOK'
        return tracking_code, status

"""
Common contract every payment-gateway adapter implements.

The rest of the codebase (services.py, views.py) only ever talks to this
interface — never to `ZarinpalAdapter` or any other concrete class directly.
That's what makes adding a new gateway (Aghaye Pardakht, a crypto
processor, ...) a matter of writing one new file + one registry line,
without touching services/views/serializers at all.
"""

from dataclasses import dataclass, field
from typing import Any


class GatewayAdapterError(Exception):
    """
    Raised by an adapter when it cannot complete a request/verify call:
    network failure, malformed response, or the gateway itself reporting
    an error. Callers (apps.orders.services) catch this and translate it
    into a business-level PaymentCreationError instead of leaking raw
    HTTP/gateway details up to the API layer.
    """


@dataclass
class PaymentRequestResult:
    """Returned by `request_payment()` on success."""

    authority: str
    redirect_url: str
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentVerifyResult:
    """Returned by `verify_payment()`, for both success and failure cases."""

    success: bool
    ref_id: str = ''
    raw_response: dict[str, Any] = field(default_factory=dict)
    error_code: str = ''
    error_message: str = ''


class BaseGatewayAdapter:
    """
    Wraps a single `Gateway` model instance and knows how to talk to that
    specific provider's API. Subclasses must implement `request_payment`
    and `verify_payment`; everything else (URLs, credential parsing, HTTP
    plumbing) is an implementation detail of the subclass.
    """

    def __init__(self, gateway):
        self.gateway = gateway

    def request_payment(
        self,
        *,
        amount: int,
        callback_url: str,
        description: str,
        mobile: str = '',
        email: str = '',
    ) -> PaymentRequestResult:
        """
        Create a payment session on the gateway's side and return a URL to
        redirect the buyer's browser to.

        Must raise GatewayAdapterError (not a bare exception) on any
        failure, so callers can handle all gateways uniformly.
        """
        raise NotImplementedError

    def verify_payment(self, *, authority: str, amount: int) -> PaymentVerifyResult:
        """
        Confirm a payment after the buyer is redirected back from the
        gateway. Must be safe to call once per transaction — callers are
        responsible for not calling it twice, but a well-behaved adapter
        should still surface the gateway's own "already verified" response
        as `success=True` rather than an error (Zarinpal, for example, has
        a dedicated code for this).
        """
        raise NotImplementedError

    @classmethod
    def extract_callback_params(cls, request) -> tuple[str, str]:
        """
        Pull (authority, status) out of the raw callback request this
        gateway sends when the buyer is redirected back.

        Every gateway uses its own HTTP method and field names here
        (Zarinpal: GET query params `Authority`/`Status`; Aqaye Pardakht:
        POST body `transid`/`status`; ...), so this is where that
        gateway-specific knowledge lives — NOT in the view. The view/service
        layer only ever sees the normalized (authority, status) tuple.

        `status` is a hint only (used to skip a pointless verify call on a
        known-failed transaction) — callers must still call
        `verify_payment()` before trusting a transaction as paid. To keep
        that shortcut logic in services.py gateway-agnostic, every adapter
        must normalize its own raw status value to the shared vocabulary
        `'OK'` (looks successful, go verify) / `'NOK'` (gateway itself
        reported failure, skip verify) — do not leak a gateway's native
        status strings/codes up to the caller.

        This is a classmethod (no gateway credentials needed) so the view
        can resolve it from `gateway_origin` alone, before a `Gateway` row
        has even been looked up.
        """
        raise NotImplementedError

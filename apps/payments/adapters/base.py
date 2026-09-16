"""
Common contract every payment-gateway adapter implements.

The rest of the codebase (services.py, views.py) only ever talks to this
interface, never to a concrete adapter class directly. That's what makes
adding a new gateway a matter of writing one new file + one registry line.
"""

from dataclasses import dataclass, field
from typing import Any


class GatewayAdapterError(Exception):
    """Raised by an adapter when a request/verify call cannot be completed."""


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
    provider's API. Subclasses must implement `request_payment` and
    `verify_payment`.
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
        redirect the buyer to. Must raise GatewayAdapterError on failure.
        """
        raise NotImplementedError

    def verify_payment(self, *, authority: str, amount: int) -> PaymentVerifyResult:
        """
        Confirm a payment after the buyer is redirected back. A well-behaved
        adapter surfaces the gateway's own "already verified" response as
        `success=True` rather than an error.
        """
        raise NotImplementedError

    @classmethod
    def extract_callback_params(cls, request) -> tuple[str, str]:
        """
        Pull (authority, status) out of the gateway's raw callback request.
        `status` is normalized to the shared vocabulary 'OK' (looks
        successful, go verify) / 'NOK' (gateway reported failure, skip
        verify) — callers must still call `verify_payment()` before
        trusting a transaction as paid.

        Classmethod (no credentials needed) so the view can resolve it from
        `gateway_origin` alone, before a `Gateway` row has been looked up.
        """
        raise NotImplementedError

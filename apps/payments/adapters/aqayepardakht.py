"""
Stub for a future Aghaye Pardakht adapter.

This is intentionally left unimplemented — it exists to show the shape a
new adapter takes. To finish it:
  1. Fill in `request_payment` / `verify_payment` against Aghaye Pardakht's
     actual REST API (base URLs, payload field names, and success/error
     codes will all differ from Zarinpal's).
  2. Register it in `registry.py` under `Gateway.Origin.AQAYEPARDAKHT`.
  3. Add a `Gateway` row with `origin="aqayepardakht"` and whatever
     credentials this adapter needs in its `credentials` JSON.

Nothing else in the codebase needs to change — services.py and views.py
are gateway-agnostic and go through `registry.get_adapter()`.
"""
from .base import BaseGatewayAdapter, GatewayAdapterError, PaymentRequestResult, PaymentVerifyResult


class AqayePardakhtAdapter(BaseGatewayAdapter):
    def request_payment(self, *, amount, callback_url, description, mobile='', email='') -> PaymentRequestResult:
        raise GatewayAdapterError('AqayePardakhtAdapter.request_payment is not implemented yet.')

    def verify_payment(self, *, authority, amount) -> PaymentVerifyResult:
        raise GatewayAdapterError('AqayePardakhtAdapter.verify_payment is not implemented yet.')
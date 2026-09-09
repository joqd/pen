"""
Single lookup point from `Gateway.origin` -> adapter class.

Services and views must always go through `get_adapter(gateway)` here,
never import a concrete adapter directly. To add a new gateway:
    1. Write `apps/payments/adapters/<name>.py` implementing BaseGatewayAdapter.
    2. Add a matching value to `Gateway.Origin` on the Gateway model.
    3. Add one line to `_ADAPTERS` below.
"""

from apps.orders.models import Gateway  # adjust import to your actual app layout

from .aqayepardakht import AqayePardakhtAdapter
from .base import BaseGatewayAdapter
from .zarinpal import ZarinpalAdapter
from .zibal import ZibalAdapter

_ADAPTERS: dict[str, type[BaseGatewayAdapter]] = {
    Gateway.Origin.ZARINPAL: ZarinpalAdapter,
    Gateway.Origin.AQAYEPARDAKHT: AqayePardakhtAdapter,  # stub — see aqayepardakht.py
    Gateway.Origin.ZIBAL: ZibalAdapter,
}


def get_adapter(gateway: Gateway) -> BaseGatewayAdapter:
    adapter_cls = _ADAPTERS.get(gateway.origin)
    if adapter_cls is None:
        raise NotImplementedError(f'No adapter registered for gateway origin "{gateway.origin}".')
    return adapter_cls(gateway)


def get_adapter_class(origin: str) -> type[BaseGatewayAdapter]:
    """
    Like `get_adapter`, but returns the class itself instead of an
    instance bound to a `Gateway` row.

    Used by the callback view to parse the gateway's raw callback request
    (`extract_callback_params`) *before* a `Gateway` has necessarily been
    looked up — that parsing needs no credentials, only knowledge of the
    gateway's callback field names/method.
    """
    adapter_cls = _ADAPTERS.get(origin)
    if adapter_cls is None:
        raise NotImplementedError(f'No adapter registered for gateway origin "{origin}".')
    return adapter_cls

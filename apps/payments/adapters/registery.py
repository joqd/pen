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

_ADAPTERS: dict[str, type[BaseGatewayAdapter]] = {
    Gateway.Origin.ZARINPAL: ZarinpalAdapter,
    Gateway.Origin.AQAYEPARDAKHT: AqayePardakhtAdapter,  # stub — see aqayepardakht.py
}


def get_adapter(gateway: Gateway) -> BaseGatewayAdapter:
    adapter_cls = _ADAPTERS.get(gateway.origin)
    if adapter_cls is None:
        raise NotImplementedError(f'No adapter registered for gateway origin "{gateway.origin}".')
    return adapter_cls(gateway)
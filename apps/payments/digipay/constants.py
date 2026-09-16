from enum import IntEnum


class TicketType(IntEnum):
    """Used as the `type` query param on verify / deliver / refund / reverse endpoints."""

    IPG = 0
    WALLET = 11
    CREDIT = 5
    BNPL = 13
    CREDIT_CARD = 24


# The `type` query param used specifically for POST /tickets/business.
# Per docs it's always 11 (UPG) regardless of the underlying payment tool.
UPG_TICKET_TYPE = 11


class PreferredGateway(IntEnum):
    """Used inside additionalInfo.preferredGateway to skip the gateway-selection screen."""

    WALLET = 0
    IPG = 2


class ProductType(IntEnum):
    DURABLE = 1
    CONSUMABLE = 2
    SERVICE = 3
    DURABLE_CONSUMABLE = 4


class SplitType:
    SIMPLE = 'simple'
    INSURANCE = 'insurance'

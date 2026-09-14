from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseDigipayService
from .constants import UPG_TICKET_TYPE, ProductType, SplitType
from .exceptions import DigipayValidationError


def _drop_none(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


@dataclass
class BasketItem:
    seller_id: str
    supplier_id: str
    product_code: str
    brand: str
    product_type: ProductType
    count: int
    category_id: str

    def to_payload(self) -> Dict[str, Any]:
        return {
            'sellerId': self.seller_id,
            'supplierId': self.supplier_id,
            'productCode': self.product_code,
            'brand': self.brand,
            'productType': int(self.product_type),
            'count': self.count,
            'categoryId': self.category_id,
        }


@dataclass
class BasketDetails:
    basket_id: str
    items: List[BasketItem]

    def to_payload(self) -> Dict[str, Any]:
        return {
            'basketId': self.basket_id,
            'items': [item.to_payload() for item in self.items],
        }


@dataclass
class Policy:
    variant_id: str
    category: str
    brand: str
    model: str
    price: int
    id: Optional[str] = None
    serial_no: Optional[str] = None
    price_with_discount: Optional[int] = None

    def to_payload(self) -> Dict[str, Any]:
        return _drop_none(
            {
                'id': self.id,
                'variantId': self.variant_id,
                'category': self.category,
                'brand': self.brand,
                'model': self.model,
                'serialNo': self.serial_no,
                'price': self.price,
                'priceWithDiscount': self.price_with_discount,
            }
        )


@dataclass
class PolicyHolder:
    first_name: str
    last_name: str
    cell_number: str
    address: str
    national_code: Optional[str] = None
    digi_plus_customer: Optional[bool] = None
    post_code: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        return _drop_none(
            {
                'nationalCode': self.national_code,
                'firstName': self.first_name,
                'lastName': self.last_name,
                'cellNumber': self.cell_number,
                'digiPlusCustomer': self.digi_plus_customer,
                'postCode': self.post_code,
                'address': self.address,
            }
        )


@dataclass
class SplitDetail:
    type: str
    username: str
    amount: int
    policies: Optional[List[Policy]] = None
    policy_holder: Optional[PolicyHolder] = None

    def __post_init__(self):
        if self.type == SplitType.INSURANCE and (not self.policies or not self.policy_holder):
            raise DigipayValidationError('policies and policy_holder are required for insurance split type')

    def to_payload(self) -> Dict[str, Any]:
        payload = {'type': self.type, 'username': self.username, 'amount': self.amount}
        if self.policies:
            payload['policies'] = [p.to_payload() for p in self.policies]
        if self.policy_holder:
            payload['policyHolder'] = self.policy_holder.to_payload()
        return payload


class DigipayTicketService(BaseDigipayService):
    """POST /tickets/business — creates a purchase ticket (BPG/CPG/Wallet/IPG)."""

    PATH = '/tickets/business'
    MAX_SPLIT_ITEMS = 2

    def create_purchase_ticket(
        self,
        cell_number: str,
        amount: int,
        provider_id: str,
        callback_url: str,
        basket_details: Optional[BasketDetails] = None,
        split_details: Optional[List[SplitDetail]] = None,
        preferred_gateway: Optional[int] = None,
        ticket_type: int = UPG_TICKET_TYPE,
    ) -> Dict[str, Any]:
        if split_details and len(split_details) > self.MAX_SPLIT_ITEMS:
            raise DigipayValidationError(f'splitDetailsList supports at most {self.MAX_SPLIT_ITEMS} items')

        payload: Dict[str, Any] = {
            'cellNumber': cell_number,
            'amount': amount,
            'providerId': provider_id,
            'callbackUrl': callback_url,
        }
        if basket_details:
            payload['basketDetailsDto'] = basket_details.to_payload()
        if split_details:
            payload['splitDetailsList'] = [s.to_payload() for s in split_details]
        if preferred_gateway is not None:
            payload['additionalInfo'] = {'preferredGateway': preferred_gateway}

        return self.request(
            method='POST',
            path=self.PATH,
            params={'type': ticket_type},
            json_data=payload,
        )

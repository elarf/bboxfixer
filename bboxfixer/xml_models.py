"""XML-based data models for BBOX fiscal printer documents.

These models are used by the XML parser and XML generator for the
raw BBOX XML protocol (BBOX_CMD / FISCAL_RECEIPT format).
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ReceiptItem:
    item_type: str
    name: str
    unit_price: str
    quantity: str
    total: str
    unit: str
    vat_rate: str
    discount: str


@dataclass
class FreeLineText:
    free_line_type: str
    index: str
    text: str
    font: Optional[str] = None
    style: Optional[str] = None
    alignment: Optional[str] = None


@dataclass
class Payment:
    payment_type: str
    currency: str
    name: str
    amount: str


@dataclass
class Address:
    company_name: str
    postal_code: str
    city: str
    street: str
    street_type: str
    street_number: str
    tax_number: str


@dataclass
class Receipt:
    total: str
    receipt_type: str = "Receipt"
    is_void: bool = False
    items: List[ReceiptItem] = field(default_factory=list)
    free_lines: List[FreeLineText] = field(default_factory=list)
    payments: List[Payment] = field(default_factory=list)


@dataclass
class StornoReceipt:
    total: str
    receipt_type: str = "Void"
    address: Optional[Address] = None
    original_receipt_number: str = ""
    date: str = ""
    register_id: str = ""
    items: List[ReceiptItem] = field(default_factory=list)
    payments: List[Payment] = field(default_factory=list)

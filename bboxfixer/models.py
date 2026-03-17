"""Data models for fiscal receipts and storno documents."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass
class ReceiptItem:
    """A single line-item on a fiscal receipt."""

    name: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal  # e.g. 27, 5, 0 (percent)

    @property
    def total_price(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": str(self.quantity),
            "unitPrice": str(self.unit_price),
            "taxRate": str(self.tax_rate),
            "totalPrice": str(self.total_price),
        }


@dataclass
class Receipt:
    """A complete fiscal receipt."""

    receipt_number: str
    date: datetime
    cashier: str
    payment_method: str  # "cash" | "card" | "voucher"
    items: List[ReceiptItem] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum(item.total_price for item in self.items)

    def to_dict(self) -> dict:
        return {
            "receiptNumber": self.receipt_number,
            "date": self.date.isoformat(),
            "cashier": self.cashier,
            "paymentMethod": self.payment_method,
            "items": [item.to_dict() for item in self.items],
            "total": str(self.total),
        }


@dataclass
class StornoReceipt:
    """A storno (cancellation / reversal) document for an original receipt."""

    original_receipt_number: str
    date: datetime
    cashier: str
    reason: str
    items: List[ReceiptItem] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum(item.total_price for item in self.items)

    def to_dict(self) -> dict:
        return {
            "originalReceiptNumber": self.original_receipt_number,
            "date": self.date.isoformat(),
            "cashier": self.cashier,
            "reason": self.reason,
            "items": [item.to_dict() for item in self.items],
            "total": str(self.total),
        }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _parse_decimal(value: str) -> Decimal:
    return Decimal(value.strip().replace(",", "."))


def _parse_datetime(value: str) -> datetime:
    """Accept ISO-8601 datetime or bare date (YYYY-MM-DD)."""
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {value!r}")


def load_receipts_from_csv(path: str) -> List[Receipt]:
    """Load receipts from a CSV file.

    Expected columns (order does not matter):
        receipt_number, date, cashier, payment_method,
        item_name, quantity, unit_price, tax_rate
    """
    receipts_map: dict[str, Receipt] = {}

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rn = row["receipt_number"].strip()
            if rn not in receipts_map:
                receipts_map[rn] = Receipt(
                    receipt_number=rn,
                    date=_parse_datetime(row["date"]),
                    cashier=row["cashier"].strip(),
                    payment_method=row["payment_method"].strip().lower(),
                )
            item = ReceiptItem(
                name=row["item_name"].strip(),
                quantity=_parse_decimal(row["quantity"]),
                unit_price=_parse_decimal(row["unit_price"]),
                tax_rate=_parse_decimal(row["tax_rate"]),
            )
            receipts_map[rn].items.append(item)

    return list(receipts_map.values())


def load_receipts_from_json(path: str) -> List[Receipt]:
    """Load receipts from a JSON file.

    The JSON file must be a list of receipt objects, each with the keys:
        receipt_number, date, cashier, payment_method, items
    where ``items`` is a list of objects with keys:
        name, quantity, unit_price, tax_rate
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    receipts: List[Receipt] = []
    for obj in data:
        items = [
            ReceiptItem(
                name=it["name"],
                quantity=_parse_decimal(str(it["quantity"])),
                unit_price=_parse_decimal(str(it["unit_price"])),
                tax_rate=_parse_decimal(str(it["tax_rate"])),
            )
            for it in obj.get("items", [])
        ]
        receipt = Receipt(
            receipt_number=str(obj["receipt_number"]),
            date=_parse_datetime(str(obj["date"])),
            cashier=str(obj["cashier"]),
            payment_method=str(obj["payment_method"]).lower(),
            items=items,
        )
        receipts.append(receipt)

    return receipts


def load_receipts(path: str) -> List[Receipt]:
    """Auto-detect file format (CSV or JSON) and load receipts."""
    if path.lower().endswith(".json"):
        return load_receipts_from_json(path)
    return load_receipts_from_csv(path)


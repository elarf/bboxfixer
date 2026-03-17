from bboxfixer.xml_models import Address, FreeLineText, Payment
from bboxfixer.xml_models import Receipt as XmlReceipt
from bboxfixer.xml_models import ReceiptItem as XmlReceiptItem
from bboxfixer.xml_models import StornoReceipt as XmlStornoReceipt


def test_receipt_item():
    item = XmlReceiptItem(
        item_type="Item",
        name="Test item",
        unit_price="500",
        quantity="2",
        total="1000",
        unit="pcs",
        vat_rate="1",
        discount="0",
    )
    assert item.name == "Test item"
    assert item.unit_price == "500"
    assert item.quantity == "2"
    assert item.total == "1000"


def test_free_line_text_defaults():
    fl = FreeLineText(free_line_type="FreeLineText", index="-1", text="Hello")
    assert fl.text == "Hello"
    assert fl.font is None
    assert fl.style is None
    assert fl.alignment is None


def test_free_line_text_full():
    fl = FreeLineText(
        free_line_type="FreeLineText",
        index="-1",
        text="Hello",
        font="None",
        style="Bold",
        alignment="CenterAligned",
    )
    assert fl.style == "Bold"
    assert fl.alignment == "CenterAligned"


def test_payment():
    p = Payment(payment_type="Cash", currency="", name="Készpénz", amount="1000")
    assert p.payment_type == "Cash"
    assert p.amount == "1000"


def test_address():
    addr = Address(
        company_name="MVM DOME",
        postal_code="1091",
        city="Budapest",
        street="Ulloi",
        street_type="a",
        street_number="133-135",
        tax_number="11111111233",
    )
    assert addr.company_name == "MVM DOME"
    assert addr.tax_number == "11111111233"


def test_receipt_defaults():
    r = XmlReceipt(total="500")
    assert r.receipt_type == "Receipt"
    assert r.is_void is False
    assert r.items == []
    assert r.free_lines == []
    assert r.payments == []


def test_storno_receipt_defaults():
    s = XmlStornoReceipt(total="500")
    assert s.receipt_type == "Void"
    assert s.address is None
    assert s.original_receipt_number == ""
    assert s.date == ""
    assert s.register_id == ""
    assert s.items == []
    assert s.payments == []


def test_receipt_with_items():
    item = XmlReceiptItem("Item", "Prod", "100", "3", "300", "kg", "2", "0")
    payment = Payment("Cash", "", "Cash", "300")
    r = XmlReceipt(total="300", items=[item], payments=[payment])
    assert len(r.items) == 1
    assert len(r.payments) == 1
"""Tests for bboxfixer.models."""

import os
import pytest
from decimal import Decimal
from datetime import datetime

from bboxfixer.models import (
    Receipt,
    ReceiptItem,
    StornoReceipt,
    load_receipts_from_csv,
    load_receipts_from_json,
    load_receipts,
    _parse_decimal,
    _parse_datetime,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
CSV_FILE = os.path.join(FIXTURES, "sample_receipts.csv")
JSON_FILE = os.path.join(FIXTURES, "sample_receipts.json")


# ---------------------------------------------------------------------------
# ReceiptItem
# ---------------------------------------------------------------------------


class TestReceiptItem:
    def test_total_price(self):
        item = ReceiptItem(
            name="Coffee",
            quantity=Decimal("2"),
            unit_price=Decimal("1.50"),
            tax_rate=Decimal("27"),
        )
        assert item.total_price == Decimal("3.00")

    def test_total_price_rounds_to_two_decimals(self):
        item = ReceiptItem(
            name="X",
            quantity=Decimal("3"),
            unit_price=Decimal("0.333"),
            tax_rate=Decimal("27"),
        )
        assert item.total_price == Decimal("1.00")

    def test_to_dict_keys(self):
        item = ReceiptItem("Tea", Decimal("1"), Decimal("2.00"), Decimal("5"))
        d = item.to_dict()
        assert set(d.keys()) == {"name", "quantity", "unitPrice", "taxRate", "totalPrice"}


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


class TestReceipt:
    def _make_receipt(self):
        return Receipt(
            receipt_number="R001",
            date=datetime(2024, 1, 15),
            cashier="John Doe",
            payment_method="cash",
            items=[
                ReceiptItem("Coffee", Decimal("2"), Decimal("1.50"), Decimal("27")),
                ReceiptItem("Sandwich", Decimal("1"), Decimal("3.00"), Decimal("5")),
            ],
        )

    def test_total(self):
        receipt = self._make_receipt()
        assert receipt.total == Decimal("6.00")

    def test_to_dict(self):
        receipt = self._make_receipt()
        d = receipt.to_dict()
        assert d["receiptNumber"] == "R001"
        assert d["cashier"] == "John Doe"
        assert d["paymentMethod"] == "cash"
        assert len(d["items"]) == 2
        assert d["total"] == "6.00"


# ---------------------------------------------------------------------------
# StornoReceipt
# ---------------------------------------------------------------------------


class TestStornoReceipt:
    def test_total(self):
        storno = StornoReceipt(
            original_receipt_number="R001",
            date=datetime(2024, 1, 16),
            cashier="Jane",
            reason="Customer request",
            items=[
                ReceiptItem("Coffee", Decimal("2"), Decimal("1.50"), Decimal("27")),
            ],
        )
        assert storno.total == Decimal("3.00")

    def test_to_dict(self):
        storno = StornoReceipt(
            original_receipt_number="R001",
            date=datetime(2024, 1, 16),
            cashier="Jane",
            reason="Return",
            items=[ReceiptItem("Coffee", Decimal("2"), Decimal("1.50"), Decimal("27"))],
        )
        d = storno.to_dict()
        assert d["originalReceiptNumber"] == "R001"
        assert d["reason"] == "Return"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestParsers:
    def test_parse_decimal_dot(self):
        assert _parse_decimal("1.50") == Decimal("1.50")

    def test_parse_decimal_comma(self):
        assert _parse_decimal("1,50") == Decimal("1.50")

    def test_parse_decimal_whitespace(self):
        assert _parse_decimal("  27 ") == Decimal("27")

    def test_parse_datetime_iso(self):
        dt = _parse_datetime("2024-01-15T10:30:00")
        assert dt == datetime(2024, 1, 15, 10, 30, 0)

    def test_parse_datetime_date_only(self):
        dt = _parse_datetime("2024-01-15")
        assert dt == datetime(2024, 1, 15)

    def test_parse_datetime_invalid(self):
        with pytest.raises(ValueError):
            _parse_datetime("not-a-date")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


class TestLoadReceiptsFromCsv:
    def test_loads_two_receipts(self):
        receipts = load_receipts_from_csv(CSV_FILE)
        # R001 and R002 and R003
        assert len(receipts) == 3

    def test_receipt_items_merged(self):
        receipts = load_receipts_from_csv(CSV_FILE)
        r001 = next(r for r in receipts if r.receipt_number == "R001")
        assert len(r001.items) == 2

    def test_payment_method_lowercase(self):
        receipts = load_receipts_from_csv(CSV_FILE)
        r002 = next(r for r in receipts if r.receipt_number == "R002")
        assert r002.payment_method == "card"

    def test_total_r001(self):
        receipts = load_receipts_from_csv(CSV_FILE)
        r001 = next(r for r in receipts if r.receipt_number == "R001")
        # 2*1.50 + 1*3.00 = 6.00
        assert r001.total == Decimal("6.00")


class TestLoadReceiptsFromJson:
    def test_loads_two_receipts(self):
        receipts = load_receipts_from_json(JSON_FILE)
        assert len(receipts) == 2

    def test_receipt_number(self):
        receipts = load_receipts_from_json(JSON_FILE)
        assert receipts[0].receipt_number == "R001"

    def test_items_loaded(self):
        receipts = load_receipts_from_json(JSON_FILE)
        assert len(receipts[0].items) == 2


class TestLoadReceiptsAutoDetect:
    def test_csv(self):
        receipts = load_receipts(CSV_FILE)
        assert len(receipts) == 3

    def test_json(self):
        receipts = load_receipts(JSON_FILE)
        assert len(receipts) == 2

"""Tests for bboxfixer.printer (payload builders and helpers)."""

import json
from decimal import Decimal
from datetime import datetime

import pytest

from bboxfixer.models import Receipt, ReceiptItem, StornoReceipt
from bboxfixer.printer import (
    build_receipt_payload,
    build_storno_payload,
    printer_base_url,
    _tax_group,
)


def _make_receipt() -> Receipt:
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


class TestPrinterBaseUrl:
    def test_default(self):
        assert printer_base_url("localhost", 5618) == "http://localhost:5618"

    def test_custom(self):
        assert printer_base_url("192.168.1.1", 8080) == "http://192.168.1.1:8080"


class TestTaxGroup:
    def test_27_percent(self):
        assert _tax_group(Decimal("27")) == 1

    def test_5_percent(self):
        assert _tax_group(Decimal("5")) == 2

    def test_0_percent(self):
        assert _tax_group(Decimal("0")) == 3

    def test_18_percent(self):
        assert _tax_group(Decimal("18")) == 4

    def test_unknown_defaults_to_1(self):
        assert _tax_group(Decimal("13")) == 1


class TestBuildReceiptPayload:
    def test_unique_sale_number(self):
        payload = build_receipt_payload(_make_receipt())
        assert payload["uniqueSaleNumber"] == "R001"

    def test_operator_code(self):
        payload = build_receipt_payload(_make_receipt())
        assert payload["operatorCode"] == "John Doe"

    def test_items_count(self):
        payload = build_receipt_payload(_make_receipt())
        assert len(payload["items"]) == 2

    def test_item_quantity(self):
        payload = build_receipt_payload(_make_receipt())
        assert payload["items"][0]["quantity"] == "2"

    def test_payment_method(self):
        payload = build_receipt_payload(_make_receipt())
        assert payload["payments"][0]["paymentType"] == "cash"

    def test_payment_amount(self):
        payload = build_receipt_payload(_make_receipt())
        # 2*1.50 + 1*3.00 = 6.00
        assert payload["payments"][0]["amount"] == "6.00"

    def test_payload_is_json_serialisable(self):
        payload = build_receipt_payload(_make_receipt())
        dumped = json.dumps(payload)
        assert "R001" in dumped


class TestBuildStornoPayload:
    def _make_storno(self) -> StornoReceipt:
        return StornoReceipt(
            original_receipt_number="R001",
            date=datetime(2024, 1, 16),
            cashier="Jane",
            reason="Return",
            items=[
                ReceiptItem("Coffee", Decimal("2"), Decimal("1.50"), Decimal("27")),
            ],
        )

    def test_unique_sale_number_has_storno_prefix(self):
        payload = build_storno_payload(self._make_storno())
        assert payload["uniqueSaleNumber"].startswith("STORNO-")

    def test_original_receipt_number(self):
        payload = build_storno_payload(self._make_storno())
        assert payload["originalReceiptNumber"] == "R001"

    def test_reason(self):
        payload = build_storno_payload(self._make_storno())
        assert payload["stornoReason"] == "Return"

    def test_negative_quantity(self):
        payload = build_storno_payload(self._make_storno())
        assert payload["items"][0]["quantity"] == "-2"

    def test_negative_payment_amount(self):
        payload = build_storno_payload(self._make_storno())
        assert float(payload["payments"][0]["amount"]) < 0

import os

import pytest

from bboxfixer.models import Receipt, StornoReceipt
from bboxfixer.parser import parse_bbox_xml

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")

with open(os.path.join(SAMPLES_DIR, "receipt.xml"), encoding="utf-8") as _f:
    RECEIPT_XML = _f.read()

with open(os.path.join(SAMPLES_DIR, "storno.xml"), encoding="utf-8") as _f:
    STORNO_XML = _f.read()


def test_parse_receipt_type():
    result = parse_bbox_xml(RECEIPT_XML)
    assert isinstance(result, Receipt)


def test_parse_receipt_fields():
    result = parse_bbox_xml(RECEIPT_XML)
    assert result.receipt_type == "Receipt"
    assert result.total == "1000"
    assert result.is_void is False


def test_parse_receipt_items():
    result = parse_bbox_xml(RECEIPT_XML)
    assert len(result.items) == 1
    item = result.items[0]
    assert item.item_type == "Item"
    assert item.name == "Termék 5-ös áfa"
    assert item.unit_price == "1000"
    assert item.quantity == "1"
    assert item.total == "1000"
    assert item.unit == "adag"
    assert item.vat_rate == "1"
    assert item.discount == "0"


def test_parse_receipt_free_lines():
    result = parse_bbox_xml(RECEIPT_XML)
    assert len(result.free_lines) == 4
    assert result.free_lines[0].text == "Fruitsys a vendeglato rendszer"
    assert result.free_lines[0].alignment == "CenterAligned"
    # Last free line has a style but no font
    last = result.free_lines[3]
    assert last.text == "10"
    assert last.style == "Bold DoubleWidth DoubleHeight"


def test_parse_receipt_payments():
    result = parse_bbox_xml(RECEIPT_XML)
    assert len(result.payments) == 1
    pay = result.payments[0]
    assert pay.payment_type == "Cash"
    assert pay.name == "Készpénz"
    assert pay.amount == "1000"


def test_parse_storno_type():
    result = parse_bbox_xml(STORNO_XML)
    assert isinstance(result, StornoReceipt)


def test_parse_storno_fields():
    result = parse_bbox_xml(STORNO_XML)
    assert result.receipt_type == "Void"
    assert result.total == "1000"
    assert result.original_receipt_number == "NY/Y23900001/0080/00016"
    assert result.date == "2026.03.16"
    assert result.register_id == "S1"


def test_parse_storno_address():
    result = parse_bbox_xml(STORNO_XML)
    assert result.address is not None
    addr = result.address
    assert addr.company_name == "MVM DOME"
    assert addr.postal_code == "1091"
    assert addr.city == "Budapest"
    assert addr.street == "Ulloi"
    assert addr.street_type == "a"
    assert addr.street_number == "133-135"
    assert addr.tax_number == "11111111233"


def test_parse_storno_items():
    result = parse_bbox_xml(STORNO_XML)
    assert len(result.items) == 1
    item = result.items[0]
    assert item.name == "Termék 5-ös áfa"


def test_parse_storno_payments():
    result = parse_bbox_xml(STORNO_XML)
    assert len(result.payments) == 1
    assert result.payments[0].name == "Forint"


def test_parse_invalid_xml():
    with pytest.raises(Exception):
        parse_bbox_xml("<not valid xml><<<")


def test_parse_missing_receipt_data():
    with pytest.raises(ValueError, match="No RECEIPT_DATA"):
        parse_bbox_xml("<BBOX_CMD><PRINTER></PRINTER></BBOX_CMD>")

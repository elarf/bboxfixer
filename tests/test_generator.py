import os
import tempfile
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime

from bboxfixer.xml_generator import build_receipt_xml, build_storno_xml, generate_bat_file, generate_bat_for_xml_file
from bboxfixer.xml_models import Address, FreeLineText, Payment, Receipt as XmlReceipt, ReceiptItem as XmlReceiptItem, StornoReceipt as XmlStornoReceipt


def _make_xml_receipt() -> XmlReceipt:
    item = XmlReceiptItem(
        item_type="Item",
        name="Test Product",
        unit_price="500",
        quantity="2",
        total="1000",
        unit="pcs",
        vat_rate="1",
        discount="0",
    )
    fl = FreeLineText(free_line_type="FreeLineText", index="-1", text="Footer text", alignment="CenterAligned")
    payment = Payment(payment_type="Cash", currency="", name="Készpénz", amount="1000")
    return XmlReceipt(total="1000", items=[item], free_lines=[fl], payments=[payment])


def _make_xml_storno() -> XmlStornoReceipt:
    address = Address(
        company_name="Test Co",
        postal_code="1000",
        city="Budapest",
        street="Main",
        street_type="st",
        street_number="1",
        tax_number="12345678901",
    )
    item = XmlReceiptItem("Item", "Test Product", "500", "2", "1000", "pcs", "1", "0")
    payment = Payment("Cash", "", "Forint", "1000")
    return XmlStornoReceipt(
        total="1000",
        address=address,
        original_receipt_number="NY/X/0001",
        date="2026.03.16",
        register_id="S1",
        items=[item],
        payments=[payment],
    )


class TestBuildReceiptXml:
    def test_produces_valid_xml(self):
        receipt = _make_xml_receipt()
        xml_str = build_receipt_xml(receipt)
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.tag == "BBOX_CMD"

    def test_has_xml_declaration(self):
        xml_str = build_receipt_xml(_make_xml_receipt())
        assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_receipt_type_element(self):
        xml_str = build_receipt_xml(_make_xml_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//RECEIPT_TYPE") == "Receipt"

    def test_total_element(self):
        xml_str = build_receipt_xml(_make_xml_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//TOTAL") == "1000"

    def test_is_void_element(self):
        xml_str = build_receipt_xml(_make_xml_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//IS_VOID") == "false"

    def test_item_elements(self):
        xml_str = build_receipt_xml(_make_xml_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        items = root.findall(".//ITEM")
        assert len(items) == 1
        assert items[0].findtext("NAME") == "Test Product"

    def test_free_line_elements(self):
        xml_str = build_receipt_xml(_make_xml_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        free_lines = root.findall(".//FREE_LINE")
        assert len(free_lines) == 1
        assert free_lines[0].findtext("TEXT") == "Footer text"

    def test_payment_elements(self):
        xml_str = build_receipt_xml(_make_xml_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        payments = root.findall(".//PAYMENT")
        assert len(payments) == 1
        assert payments[0].findtext("PAYMENT_TYPE") == "Cash"

    def test_structure(self):
        xml_str = build_receipt_xml(_make_xml_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.find("PRINTER") is not None
        assert root.find(".//FISCAL_RECEIPT") is not None
        assert root.find(".//RECEIPT_DATA") is not None


class TestBuildStornoXml:
    def test_produces_valid_xml(self):
        storno = _make_xml_storno()
        xml_str = build_storno_xml(storno)
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.tag == "BBOX_CMD"

    def test_has_xml_declaration(self):
        xml_str = build_storno_xml(_make_xml_storno())
        assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_receipt_type_void(self):
        xml_str = build_storno_xml(_make_xml_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//RECEIPT_TYPE") == "Void"

    def test_address_elements(self):
        xml_str = build_storno_xml(_make_xml_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//COMPANY_NAME") == "Test Co"
        assert root.findtext(".//TAX_NUMBER") == "12345678901"

    def test_original_receipt_number(self):
        xml_str = build_storno_xml(_make_xml_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//ORIGINAL_RECEIPT_NUMBER") == "NY/X/0001"

    def test_date_and_register_id(self):
        xml_str = build_storno_xml(_make_xml_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//DATE") == "2026.03.16"
        assert root.findtext(".//REGISTER_ID") == "S1"

    def test_item_elements(self):
        xml_str = build_storno_xml(_make_xml_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        items = root.findall(".//ITEM")
        assert len(items) == 1

    def test_payment_elements(self):
        xml_str = build_storno_xml(_make_xml_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        payments = root.findall(".//PAYMENT")
        assert len(payments) == 1
        assert payments[0].findtext("NAME") == "Forint"

    def test_no_address_when_none(self):
        storno = XmlStornoReceipt(total="0")
        xml_str = build_storno_xml(storno)
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.find(".//ADDRESS") is None


class TestGenerateBatFile:
    def test_contains_echo_off(self):
        content = generate_bat_file("receipt.xml", "localhost", 8080)
        assert "@echo off" in content

    def test_contains_curl_command(self):
        content = generate_bat_file("receipt.xml", "localhost", 8080)
        assert "curl -X POST" in content

    def test_contains_correct_url(self):
        content = generate_bat_file("receipt.xml", "192.168.1.10", 9090)
        assert "http://192.168.1.10:9090/api/printer/fiscal_receipt" in content

    def test_contains_xml_filename(self):
        content = generate_bat_file("receipt.xml", "localhost", 8080)
        assert "receipt.xml" in content

    def test_response_filename_derived_from_xml(self):
        content = generate_bat_file("my_receipt.xml", "localhost", 8080)
        assert "my_receipt_response.txt" in content

    def test_content_type_header(self):
        content = generate_bat_file("receipt.xml", "localhost", 8080)
        assert "Content-Type: text/xml;charset=UTF-8" in content

    def test_silent_show_error_flags(self):
        content = generate_bat_file("receipt.xml", "localhost", 8080)
        assert "--silent --show-error" in content

    def test_data_binary_flag(self):
        content = generate_bat_file("receipt.xml", "localhost", 8080)
        assert "--data-binary" in content


class TestGenerateBatForXmlFile:
    def test_creates_bat_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = os.path.join(tmpdir, "test_receipt.xml")
            with open(xml_path, "w") as f:
                f.write("<BBOX_CMD/>")
            bat_path = generate_bat_for_xml_file(xml_path, tmpdir, "localhost", 8080)
            assert os.path.isfile(bat_path)
            assert bat_path.endswith("test_receipt.bat")

    def test_bat_file_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = os.path.join(tmpdir, "invoice.xml")
            with open(xml_path, "w") as f:
                f.write("<BBOX_CMD/>")
            bat_path = generate_bat_for_xml_file(xml_path, tmpdir, "printer.local", 8888)
            with open(bat_path, encoding="utf-8") as f:
                content = f.read()
            assert "http://printer.local:8888/api/printer/fiscal_receipt" in content
            assert "invoice.xml" in content


# ---------------------------------------------------------------------------
# New tests for BatFileGenerator
# ---------------------------------------------------------------------------

import json
import pytest

from bboxfixer.generator import BatFileGenerator, _escape_for_bat
from bboxfixer.models import Receipt, ReceiptItem, StornoReceipt, load_receipts_from_csv

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
CSV_FILE = os.path.join(FIXTURES, "sample_receipts.csv")


def _make_receipt(receipt_number="R001") -> Receipt:
    return Receipt(
        receipt_number=receipt_number,
        date=datetime(2024, 1, 15),
        cashier="John Doe",
        payment_method="cash",
        items=[
            ReceiptItem("Coffee", Decimal("2"), Decimal("1.50"), Decimal("27")),
            ReceiptItem("Sandwich", Decimal("1"), Decimal("3.00"), Decimal("5")),
        ],
    )


# ---------------------------------------------------------------------------
# _escape_for_bat
# ---------------------------------------------------------------------------


class TestEscapeForBat:
    def test_escapes_double_quotes(self):
        result = _escape_for_bat('{"key":"value"}')
        assert '\\"' in result
        assert '"' not in result.replace('\\"', "")

    def test_escapes_percent(self):
        result = _escape_for_bat("100%")
        assert "%%" in result

    def test_plain_string_unchanged(self):
        result = _escape_for_bat("hello world")
        assert result == "hello world"


# ---------------------------------------------------------------------------
# BatFileGenerator – reprint
# ---------------------------------------------------------------------------


class TestGenerateReprintBat:
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(host="192.168.1.100", port=5618, output_dir=tmpdir)
            path = gen.generate_reprint_bat(_make_receipt())
            assert os.path.exists(path)

    def test_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_reprint_bat(_make_receipt("R001"))
            assert os.path.basename(path) == "reprint_R001.bat"

    def test_content_contains_receipt_number(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(host="192.168.1.1", port=5618, output_dir=tmpdir)
            path = gen.generate_reprint_bat(_make_receipt("R999"))
            content = open(path).read()
            assert "R999" in content

    def test_content_contains_host(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(host="10.0.0.5", port=5618, output_dir=tmpdir)
            path = gen.generate_reprint_bat(_make_receipt())
            content = open(path).read()
            assert "10.0.0.5" in content

    def test_content_contains_curl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_reprint_bat(_make_receipt())
            content = open(path).read()
            assert "curl" in content.lower()

    def test_content_uses_reprint_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_reprint_bat(_make_receipt())
            content = open(path).read()
            assert "/peri/print/reprint" in content

    def test_windows_line_endings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_reprint_bat(_make_receipt())
            raw = open(path, "rb").read()
            assert b"\r\n" in raw


# ---------------------------------------------------------------------------
# BatFileGenerator – storno
# ---------------------------------------------------------------------------


class TestGenerateStornoBat:
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_storno_bat(_make_receipt())
            assert os.path.exists(path)

    def test_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_storno_bat(_make_receipt("R002"))
            assert os.path.basename(path) == "storno_R002.bat"

    def test_content_contains_original_receipt_number(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_storno_bat(_make_receipt("R001"))
            content = open(path).read()
            assert "R001" in content

    def test_content_uses_print_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_storno_bat(_make_receipt())
            content = open(path).read()
            assert "/peri/print" in content

    def test_storno_payload_has_negative_quantities(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_storno_bat(_make_receipt())
            content = open(path).read()
            assert "-2" in content or "-1" in content

    def test_custom_reason_in_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            path = gen.generate_storno_bat(_make_receipt(), reason="Customer request")
            content = open(path).read()
            assert "Customer request" in content


# ---------------------------------------------------------------------------
# BatFileGenerator – generate_all
# ---------------------------------------------------------------------------


class TestGenerateAll:
    def test_mode_both_generates_two_files_per_receipt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            receipts = load_receipts_from_csv(CSV_FILE)
            paths = gen.generate_all(receipts, mode="both")
            # 3 receipts * 2 files = 6
            assert len(paths) == 6

    def test_mode_reprint_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            receipts = load_receipts_from_csv(CSV_FILE)
            paths = gen.generate_all(receipts, mode="reprint")
            assert len(paths) == 3
            assert all("reprint" in os.path.basename(p) for p in paths)

    def test_mode_storno_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = BatFileGenerator(output_dir=tmpdir)
            receipts = load_receipts_from_csv(CSV_FILE)
            paths = gen.generate_all(receipts, mode="storno")
            assert len(paths) == 3
            assert all("storno" in os.path.basename(p) for p in paths)

    def test_invalid_mode_raises(self):
        gen = BatFileGenerator()
        with pytest.raises(ValueError, match="Invalid mode"):
            gen.generate_all([], mode="unknown")

    def test_output_dir_created(self):
        with tempfile.TemporaryDirectory() as parent:
            out = os.path.join(parent, "new_output_dir")
            gen = BatFileGenerator(output_dir=out)
            gen.generate_all([_make_receipt()], mode="reprint")
            assert os.path.isdir(out)

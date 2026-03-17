import os
import tempfile
import xml.etree.ElementTree as ET

from bboxfixer.generator import build_receipt_xml, build_storno_xml, generate_bat_file, generate_bat_for_xml_file
from bboxfixer.models import Address, FreeLineText, Payment, Receipt, ReceiptItem, StornoReceipt


def _make_receipt() -> Receipt:
    item = ReceiptItem(
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
    return Receipt(total="1000", items=[item], free_lines=[fl], payments=[payment])


def _make_storno() -> StornoReceipt:
    address = Address(
        company_name="Test Co",
        postal_code="1000",
        city="Budapest",
        street="Main",
        street_type="st",
        street_number="1",
        tax_number="12345678901",
    )
    item = ReceiptItem("Item", "Test Product", "500", "2", "1000", "pcs", "1", "0")
    payment = Payment("Cash", "", "Forint", "1000")
    return StornoReceipt(
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
        receipt = _make_receipt()
        xml_str = build_receipt_xml(receipt)
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.tag == "BBOX_CMD"

    def test_has_xml_declaration(self):
        xml_str = build_receipt_xml(_make_receipt())
        assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_receipt_type_element(self):
        xml_str = build_receipt_xml(_make_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//RECEIPT_TYPE") == "Receipt"

    def test_total_element(self):
        xml_str = build_receipt_xml(_make_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//TOTAL") == "1000"

    def test_is_void_element(self):
        xml_str = build_receipt_xml(_make_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//IS_VOID") == "false"

    def test_item_elements(self):
        xml_str = build_receipt_xml(_make_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        items = root.findall(".//ITEM")
        assert len(items) == 1
        assert items[0].findtext("NAME") == "Test Product"

    def test_free_line_elements(self):
        xml_str = build_receipt_xml(_make_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        free_lines = root.findall(".//FREE_LINE")
        assert len(free_lines) == 1
        assert free_lines[0].findtext("TEXT") == "Footer text"

    def test_payment_elements(self):
        xml_str = build_receipt_xml(_make_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        payments = root.findall(".//PAYMENT")
        assert len(payments) == 1
        assert payments[0].findtext("PAYMENT_TYPE") == "Cash"

    def test_structure(self):
        xml_str = build_receipt_xml(_make_receipt())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.find("PRINTER") is not None
        assert root.find(".//FISCAL_RECEIPT") is not None
        assert root.find(".//RECEIPT_DATA") is not None


class TestBuildStornoXml:
    def test_produces_valid_xml(self):
        storno = _make_storno()
        xml_str = build_storno_xml(storno)
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.tag == "BBOX_CMD"

    def test_has_xml_declaration(self):
        xml_str = build_storno_xml(_make_storno())
        assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_receipt_type_void(self):
        xml_str = build_storno_xml(_make_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//RECEIPT_TYPE") == "Void"

    def test_address_elements(self):
        xml_str = build_storno_xml(_make_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//COMPANY_NAME") == "Test Co"
        assert root.findtext(".//TAX_NUMBER") == "12345678901"

    def test_original_receipt_number(self):
        xml_str = build_storno_xml(_make_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//ORIGINAL_RECEIPT_NUMBER") == "NY/X/0001"

    def test_date_and_register_id(self):
        xml_str = build_storno_xml(_make_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        assert root.findtext(".//DATE") == "2026.03.16"
        assert root.findtext(".//REGISTER_ID") == "S1"

    def test_item_elements(self):
        xml_str = build_storno_xml(_make_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        items = root.findall(".//ITEM")
        assert len(items) == 1

    def test_payment_elements(self):
        xml_str = build_storno_xml(_make_storno())
        root = ET.fromstring(xml_str.split("\n", 1)[1])
        payments = root.findall(".//PAYMENT")
        assert len(payments) == 1
        assert payments[0].findtext("NAME") == "Forint"

    def test_no_address_when_none(self):
        storno = StornoReceipt(total="0")
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

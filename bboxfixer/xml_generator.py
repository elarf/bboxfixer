"""XML-based bat-file generator for BBOX fiscal printer operations.

Generates BBOX XML documents and the corresponding Windows .bat files
that send them to the printer via curl.
"""

import os
import xml.etree.ElementTree as ET

from .xml_models import Address, FreeLineText, Payment, Receipt, ReceiptItem, StornoReceipt


def _sub(parent: ET.Element, tag: str, text: str = "") -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _build_item_element(parent: ET.Element, item: ReceiptItem) -> None:
    item_el = ET.SubElement(parent, "ITEM")
    _sub(item_el, "ITEM_TYPE", item.item_type)
    _sub(item_el, "NAME", item.name)
    _sub(item_el, "UNIT_PRICE", item.unit_price)
    _sub(item_el, "QUANTITY", item.quantity)
    _sub(item_el, "TOTAL", item.total)
    _sub(item_el, "UNIT", item.unit)
    _sub(item_el, "VAT_RATE", item.vat_rate)
    _sub(item_el, "DISCOUNT", item.discount)


def _build_free_line_element(parent: ET.Element, fl: FreeLineText) -> None:
    fl_el = ET.SubElement(parent, "FREE_LINE")
    _sub(fl_el, "FREE_LINE_TYPE", fl.free_line_type)
    _sub(fl_el, "INDEX", fl.index)
    _sub(fl_el, "TEXT", fl.text)
    if fl.font is not None:
        _sub(fl_el, "FONT", fl.font)
    if fl.style is not None:
        _sub(fl_el, "STYLE", fl.style)
    if fl.alignment is not None:
        _sub(fl_el, "ALIGNMENT", fl.alignment)


def _build_payment_element(parent: ET.Element, payment: Payment) -> None:
    pay_el = ET.SubElement(parent, "PAYMENT")
    _sub(pay_el, "PAYMENT_TYPE", payment.payment_type)
    _sub(pay_el, "CURRENCY", payment.currency)
    _sub(pay_el, "NAME", payment.name)
    _sub(pay_el, "AMOUNT", payment.amount)


def _build_address_element(parent: ET.Element, address: Address) -> None:
    addr_el = ET.SubElement(parent, "ADDRESS")
    _sub(addr_el, "COMPANY_NAME", address.company_name)
    _sub(addr_el, "POSTAL_CODE", address.postal_code)
    _sub(addr_el, "CITY", address.city)
    _sub(addr_el, "STREET", address.street)
    _sub(addr_el, "STREET_TYPE", address.street_type)
    _sub(addr_el, "STREET_NUMBER", address.street_number)
    _sub(addr_el, "TAX_NUMBER", address.tax_number)


def build_receipt_xml(receipt: Receipt) -> str:
    root = ET.Element("BBOX_CMD")
    printer = ET.SubElement(root, "PRINTER")
    fiscal = ET.SubElement(printer, "FISCAL_RECEIPT")
    data = ET.SubElement(fiscal, "RECEIPT_DATA")

    _sub(data, "RECEIPT_TYPE", receipt.receipt_type)
    _sub(data, "TOTAL", receipt.total)
    _sub(data, "IS_VOID", str(receipt.is_void).lower())

    for item in receipt.items:
        _build_item_element(data, item)
    for fl in receipt.free_lines:
        _build_free_line_element(data, fl)
    for payment in receipt.payments:
        _build_payment_element(data, payment)

    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str


def build_storno_xml(storno: StornoReceipt) -> str:
    root = ET.Element("BBOX_CMD")
    printer = ET.SubElement(root, "PRINTER")
    fiscal = ET.SubElement(printer, "FISCAL_RECEIPT")
    data = ET.SubElement(fiscal, "RECEIPT_DATA")

    _sub(data, "RECEIPT_TYPE", storno.receipt_type)
    _sub(data, "TOTAL", storno.total)

    if storno.address is not None:
        _build_address_element(data, storno.address)

    _sub(data, "ORIGINAL_RECEIPT_NUMBER", storno.original_receipt_number)
    _sub(data, "DATE", storno.date)
    _sub(data, "REGISTER_ID", storno.register_id)

    for item in storno.items:
        _build_item_element(data, item)
    for payment in storno.payments:
        _build_payment_element(data, payment)

    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str


def generate_bat_file(xml_filename: str, host: str, port: int) -> str:
    stem = os.path.splitext(xml_filename)[0]
    response_filename = stem + "_response.txt"
    return (
        "@echo off\n"
        f"echo Sending BBOX receipt to printer...\n"
        f'curl -X POST "http://{host}:{port}/api/printer/fiscal_receipt" ^\n'
        f'  -H "Content-Type: text/xml;charset=UTF-8" ^\n'
        f'  --data-binary @"%~dp0{xml_filename}" ^\n'
        f'  -o "%~dp0{response_filename}" ^\n'
        f"  --silent --show-error\n"
        f"echo Done. Response saved to {response_filename}.\n"
    )


def generate_bat_for_xml_file(xml_path: str, output_dir: str, host: str, port: int) -> str:
    xml_filename = os.path.basename(xml_path)
    stem = os.path.splitext(xml_filename)[0]
    bat_filename = stem + ".bat"

    bat_content = generate_bat_file(xml_filename, host, port)

    bat_path = os.path.join(output_dir, bat_filename)
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    return bat_path

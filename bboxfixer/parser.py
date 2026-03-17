import xml.etree.ElementTree as ET
from typing import Union

from .xml_models import Address, FreeLineText, Payment, Receipt, ReceiptItem, StornoReceipt


def _text(element: ET.Element, tag: str, default: str = "") -> str:
    child = element.find(tag)
    if child is None or child.text is None:
        return default
    return child.text


def _parse_item(item_el: ET.Element) -> ReceiptItem:
    return ReceiptItem(
        item_type=_text(item_el, "ITEM_TYPE"),
        name=_text(item_el, "NAME"),
        unit_price=_text(item_el, "UNIT_PRICE"),
        quantity=_text(item_el, "QUANTITY"),
        total=_text(item_el, "TOTAL"),
        unit=_text(item_el, "UNIT"),
        vat_rate=_text(item_el, "VAT_RATE"),
        discount=_text(item_el, "DISCOUNT"),
    )


def _parse_free_line(fl_el: ET.Element) -> FreeLineText:
    return FreeLineText(
        free_line_type=_text(fl_el, "FREE_LINE_TYPE"),
        index=_text(fl_el, "INDEX"),
        text=_text(fl_el, "TEXT"),
        font=_text(fl_el, "FONT") or None,
        style=_text(fl_el, "STYLE") or None,
        alignment=_text(fl_el, "ALIGNMENT") or None,
    )


def _parse_payment(pay_el: ET.Element) -> Payment:
    currency_el = pay_el.find("CURRENCY")
    currency = "" if currency_el is None or currency_el.text is None else currency_el.text
    return Payment(
        payment_type=_text(pay_el, "PAYMENT_TYPE"),
        currency=currency,
        name=_text(pay_el, "NAME"),
        amount=_text(pay_el, "AMOUNT"),
    )


def _parse_address(addr_el: ET.Element) -> Address:
    return Address(
        company_name=_text(addr_el, "COMPANY_NAME"),
        postal_code=_text(addr_el, "POSTAL_CODE"),
        city=_text(addr_el, "CITY"),
        street=_text(addr_el, "STREET"),
        street_type=_text(addr_el, "STREET_TYPE"),
        street_number=_text(addr_el, "STREET_NUMBER"),
        tax_number=_text(addr_el, "TAX_NUMBER"),
    )


def parse_receipt(data_el: ET.Element) -> Receipt:
    is_void_text = _text(data_el, "IS_VOID", "false").lower()
    items = [_parse_item(el) for el in data_el.findall("ITEM")]
    free_lines = [_parse_free_line(el) for el in data_el.findall("FREE_LINE")]
    payments = [_parse_payment(el) for el in data_el.findall("PAYMENT")]
    return Receipt(
        receipt_type=_text(data_el, "RECEIPT_TYPE", "Receipt"),
        total=_text(data_el, "TOTAL"),
        is_void=is_void_text == "true",
        items=items,
        free_lines=free_lines,
        payments=payments,
    )


def parse_storno(data_el: ET.Element) -> StornoReceipt:
    addr_el = data_el.find("ADDRESS")
    address = _parse_address(addr_el) if addr_el is not None else None
    items = [_parse_item(el) for el in data_el.findall("ITEM")]
    payments = [_parse_payment(el) for el in data_el.findall("PAYMENT")]
    return StornoReceipt(
        receipt_type=_text(data_el, "RECEIPT_TYPE", "Void"),
        total=_text(data_el, "TOTAL"),
        address=address,
        original_receipt_number=_text(data_el, "ORIGINAL_RECEIPT_NUMBER"),
        date=_text(data_el, "DATE"),
        register_id=_text(data_el, "REGISTER_ID"),
        items=items,
        payments=payments,
    )


def parse_bbox_xml(xml_content: str) -> Union[Receipt, StornoReceipt]:
    root = ET.fromstring(xml_content)
    data_el = root.find(".//RECEIPT_DATA")
    if data_el is None:
        raise ValueError("No RECEIPT_DATA element found in XML")
    receipt_type = _text(data_el, "RECEIPT_TYPE", "Receipt")
    if receipt_type == "Void":
        return parse_storno(data_el)
    return parse_receipt(data_el)

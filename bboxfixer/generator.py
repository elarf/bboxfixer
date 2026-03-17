import os
import xml.etree.ElementTree as ET

from .models import Address, FreeLineText, Payment, Receipt, ReceiptItem, StornoReceipt


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
"""Bat-file generator for BBOX fiscal printer operations."""

from __future__ import annotations

import json
import os
from typing import List, Optional

from .models import Receipt, StornoReceipt
from .printer import (
    ENDPOINT_PRINT,
    ENDPOINT_REPRINT,
    build_receipt_payload,
    build_storno_payload,
    printer_base_url,
)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_BAT_HEADER = """\
@echo off
REM Generated by bboxfixer
REM {description}
"""

_CURL_REPRINT = """\
curl -s -X POST "{base_url}{endpoint}?FN={fiscal_number}" ^
  -o NUL
if %errorlevel% neq 0 (
    echo ERROR: reprint failed for receipt {fiscal_number}
    exit /b %errorlevel%
)
echo Reprint sent for receipt {fiscal_number}
"""

_CURL_PRINT = """\
curl -s -X POST "{base_url}{endpoint}" ^
  -H "Content-Type: application/json" ^
  -d "{payload}" ^
  -o NUL
if %errorlevel% neq 0 (
    echo ERROR: print command failed
    exit /b %errorlevel%
)
echo Print command sent
"""

_BAT_FOOTER = """\
echo Done.
"""


def _escape_for_bat(json_str: str) -> str:
    """Escape a JSON string so it is safe inside Windows bat double-quotes.

    Specifically:
    * Double-quotes become ``\\"`` so the shell sees ``"``
    * Percent signs are doubled (``%%``) to avoid variable expansion
    """
    json_str = json_str.replace('"', '\\"')
    json_str = json_str.replace("%", "%%")
    return json_str


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class BatFileGenerator:
    """Generate ``.bat`` files that reprint or storno BBOX fiscal receipts.

    Parameters
    ----------
    host:
        IP address or hostname of the BBOX fiscal printer (or its middleware).
    port:
        HTTP port of the BBOX middleware (default: 5618).
    output_dir:
        Directory where the generated ``.bat`` files will be written.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5618,
        output_dir: str = "output",
    ) -> None:
        self.host = host
        self.port = port
        self.output_dir = output_dir
        self._base_url = printer_base_url(host, port)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_reprint_bat(self, receipt: Receipt) -> str:
        """Generate a ``.bat`` file that reprints *receipt* and return its path."""
        filename = f"reprint_{receipt.receipt_number}.bat"
        content = self._reprint_bat_content(receipt)
        return self._write_bat(filename, content)

    def generate_storno_bat(self, receipt: Receipt, reason: str = "Cancellation") -> str:
        """Generate a ``.bat`` file for a storno document and return its path."""
        storno = StornoReceipt(
            original_receipt_number=receipt.receipt_number,
            date=receipt.date,
            cashier=receipt.cashier,
            reason=reason,
            items=receipt.items,
        )
        filename = f"storno_{receipt.receipt_number}.bat"
        content = self._storno_bat_content(storno)
        return self._write_bat(filename, content)

    def generate_all(
        self,
        receipts: List[Receipt],
        mode: str = "both",
        storno_reason: str = "Cancellation",
    ) -> List[str]:
        """Generate bat files for a list of receipts.

        Parameters
        ----------
        receipts:
            Receipts to process.
        mode:
            One of ``"reprint"``, ``"storno"``, or ``"both"``.
        storno_reason:
            Reason text added to every storno document.

        Returns
        -------
        List of file paths that were written.
        """
        if mode not in {"reprint", "storno", "both"}:
            raise ValueError(f"Invalid mode {mode!r}; choose reprint, storno, or both")

        os.makedirs(self.output_dir, exist_ok=True)
        paths: List[str] = []

        for receipt in receipts:
            if mode in ("reprint", "both"):
                paths.append(self.generate_reprint_bat(receipt))
            if mode in ("storno", "both"):
                paths.append(self.generate_storno_bat(receipt, reason=storno_reason))

        return paths

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _reprint_bat_content(self, receipt: Receipt) -> str:
        header = _BAT_HEADER.format(
            description=f"Reprint receipt {receipt.receipt_number}"
        )
        body = _CURL_REPRINT.format(
            base_url=self._base_url,
            endpoint=ENDPOINT_REPRINT,
            fiscal_number=receipt.receipt_number,
        )
        return header + body + _BAT_FOOTER

    def _storno_bat_content(self, storno_receipt: StornoReceipt) -> str:
        payload = build_storno_payload(storno_receipt)
        payload_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        escaped = _escape_for_bat(payload_str)

        header = _BAT_HEADER.format(
            description=f"Storno for receipt {storno_receipt.original_receipt_number}"
        )
        body = _CURL_PRINT.format(
            base_url=self._base_url,
            endpoint=ENDPOINT_PRINT,
            payload=escaped,
        )
        return header + body + _BAT_FOOTER

    def _write_bat(self, filename: str, content: str) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write(content)
        return path

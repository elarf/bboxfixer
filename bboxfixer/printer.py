"""BBOX fiscal printer protocol helpers.

Based on the EFR (Electronic Fiscal Register) HTTP API used by BBOX
fiscal printers for Hungarian fiscalisation.

Relevant endpoints:
    POST /peri/print                  – print a new receipt / storno receipt
    POST /peri/print/reprint?FN=<n>   – reprint an existing receipt by
                                         its fiscal number (FN)
"""

from __future__ import annotations

import json
from decimal import Decimal

from .models import Receipt, StornoReceipt

# Default connection parameters; may be overridden by CLI flags or config.
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5618

ENDPOINT_PRINT = "/peri/print"
ENDPOINT_REPRINT = "/peri/print/reprint"


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def build_receipt_payload(receipt: Receipt) -> dict:
    """Build the JSON payload for printing/reprinting a receipt."""
    return {
        "uniqueSaleNumber": receipt.receipt_number,
        "operatorCode": receipt.cashier,
        "items": [
            {
                "text": item.name,
                "quantity": str(item.quantity),
                "unitPrice": str(item.unit_price),
                "taxGroup": _tax_group(item.tax_rate),
            }
            for item in receipt.items
        ],
        "payments": [
            {
                "paymentType": receipt.payment_method,
                "amount": str(receipt.total),
            }
        ],
    }


def build_storno_payload(storno: StornoReceipt) -> dict:
    """Build the JSON payload for a storno (reversal) receipt.

    Storno items carry *negative* quantities so the fiscal printer
    records the cancellation correctly.
    """
    return {
        "uniqueSaleNumber": f"STORNO-{storno.original_receipt_number}",
        "operatorCode": storno.cashier,
        "stornoReason": storno.reason,
        "originalReceiptNumber": storno.original_receipt_number,
        "items": [
            {
                "text": item.name,
                "quantity": str(-abs(item.quantity)),
                "unitPrice": str(item.unit_price),
                "taxGroup": _tax_group(item.tax_rate),
            }
            for item in storno.items
        ],
        "payments": [
            {
                "paymentType": "cash",
                "amount": str(-abs(storno.total)),
            }
        ],
    }


def printer_base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tax_group(rate: Decimal) -> int:
    """Map a tax rate percentage to a BBOX tax group number.

    BBOX uses integer group codes:
        1 – 27 %   (standard VAT in Hungary)
        2 –  5 %   (reduced VAT)
        3 –  0 %   (zero-rated / exempt)
        4 – 18 %   (intermediate rate)
    """
    mapping = {
        Decimal("27"): 1,
        Decimal("18"): 4,
        Decimal("5"): 2,
        Decimal("0"): 3,
    }
    return mapping.get(rate, 1)

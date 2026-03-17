"""Tests for bboxfixer.generator."""

import json
import os
import tempfile
from decimal import Decimal
from datetime import datetime

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

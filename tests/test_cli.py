"""Tests for bboxfixer CLI."""

import os
import sys
import tempfile

import pytest

from bboxfixer.cli import main, parse_args

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
CSV_FILE = os.path.join(FIXTURES, "sample_receipts.csv")
JSON_FILE = os.path.join(FIXTURES, "sample_receipts.json")


class TestParseArgs:
    def test_input_required(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_defaults(self):
        args = parse_args([CSV_FILE])
        assert args.input == CSV_FILE
        assert args.output_dir == "output"
        assert args.host == "localhost"
        assert args.port == 5618
        assert args.mode == "both"
        assert args.storno_reason == "Cancellation"

    def test_custom_host_port(self):
        args = parse_args([CSV_FILE, "--host", "10.0.0.1", "--port", "8080"])
        assert args.host == "10.0.0.1"
        assert args.port == 8080

    def test_mode_reprint(self):
        args = parse_args([CSV_FILE, "--mode", "reprint"])
        assert args.mode == "reprint"

    def test_mode_storno(self):
        args = parse_args([CSV_FILE, "--mode", "storno"])
        assert args.mode == "storno"

    def test_invalid_mode(self):
        with pytest.raises(SystemExit):
            parse_args([CSV_FILE, "--mode", "invalid"])


class TestMain:
    def test_main_csv_both(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rc = main([CSV_FILE, "-o", tmpdir, "--mode", "both"])
            assert rc == 0
            files = os.listdir(tmpdir)
            # 3 receipts * 2 = 6 bat files
            assert len(files) == 6

    def test_main_json_reprint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rc = main([JSON_FILE, "-o", tmpdir, "--mode", "reprint"])
            assert rc == 0
            files = os.listdir(tmpdir)
            # 2 receipts * 1 = 2 bat files
            assert len(files) == 2

    def test_main_missing_file(self):
        rc = main(["nonexistent_file.csv", "-o", "/tmp"])
        assert rc == 1

    def test_main_storno_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rc = main([
                CSV_FILE, "-o", tmpdir, "--mode", "storno",
                "--storno-reason", "Customer return",
            ])
            assert rc == 0
            bat_files = [f for f in os.listdir(tmpdir) if f.startswith("storno_")]
            content = open(os.path.join(tmpdir, bat_files[0])).read()
            assert "Customer return" in content

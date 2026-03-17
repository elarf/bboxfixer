# bboxfixer

A Python tool that generates Windows `.bat` files containing `curl` commands so that BBOX fiscal printer receipts and storno (void) documents can be reprinted.

## Installation

```bash
pip install -e .
```

## Usage

```
bboxfixer [--host HOST] [--port PORT] [--output-dir OUTPUT_DIR] xml_files...
```

### Arguments

| Argument | Description | Default |
|---|---|---|
| `xml_files` | One or more BBOX XML files to process | *(required)* |
| `--host` | Printer host | `localhost` |
| `--port` | Printer port | `8080` |
| `--output-dir` | Directory for output `.bat` files | Same directory as input file |

### Examples

Process a single file with defaults:
```bash
bboxfixer samples/receipt.xml
```

Process multiple files with a custom host/port:
```bash
bboxfixer --host 192.168.1.50 --port 9090 receipt.xml storno.xml
```

Write all `.bat` files to a specific output directory:
```bash
bboxfixer --output-dir /tmp/bats samples/receipt.xml samples/storno.xml
```

## Generated `.bat` file

For an input file `receipt.xml` the tool generates `receipt.bat`:

```bat
@echo off
echo Sending BBOX receipt to printer...
curl -X POST "http://localhost:8080/api/printer/fiscal_receipt" ^
  -H "Content-Type: text/xml;charset=UTF-8" ^
  --data-binary @"%~dp0receipt.xml" ^
  -o "%~dp0receipt_response.txt" ^
  --silent --show-error
echo Done. Response saved to receipt_response.txt.
```

Running the `.bat` file POSTs the XML to the printer and saves the server response to `<stem>_response.txt` in the same directory.

## Supported document types

| `RECEIPT_TYPE` | Description |
|---|---|
| `Receipt` | Standard fiscal receipt |
| `Void` | Storno / void document |

## Running tests

```bash
pip install pytest
pytest
```

## Project structure

```
bboxfixer/
├── bboxfixer/
│   ├── __init__.py
│   ├── models.py      # Dataclasses for receipt/storno data
│   ├── parser.py      # XML → dataclass parsing
│   ├── generator.py   # Dataclass → XML and .bat generation
│   └── cli.py         # Command-line interface
├── tests/
│   ├── test_models.py
│   ├── test_parser.py
│   └── test_generator.py
├── samples/
│   ├── receipt.xml
│   └── storno.xml
├── pyproject.toml
└── requirements.txt
```

from bboxfixer.models import Address, FreeLineText, Payment, Receipt, ReceiptItem, StornoReceipt


def test_receipt_item():
    item = ReceiptItem(
        item_type="Item",
        name="Test item",
        unit_price="500",
        quantity="2",
        total="1000",
        unit="pcs",
        vat_rate="1",
        discount="0",
    )
    assert item.name == "Test item"
    assert item.unit_price == "500"
    assert item.quantity == "2"
    assert item.total == "1000"


def test_free_line_text_defaults():
    fl = FreeLineText(free_line_type="FreeLineText", index="-1", text="Hello")
    assert fl.text == "Hello"
    assert fl.font is None
    assert fl.style is None
    assert fl.alignment is None


def test_free_line_text_full():
    fl = FreeLineText(
        free_line_type="FreeLineText",
        index="-1",
        text="Hello",
        font="None",
        style="Bold",
        alignment="CenterAligned",
    )
    assert fl.style == "Bold"
    assert fl.alignment == "CenterAligned"


def test_payment():
    p = Payment(payment_type="Cash", currency="", name="Készpénz", amount="1000")
    assert p.payment_type == "Cash"
    assert p.amount == "1000"


def test_address():
    addr = Address(
        company_name="MVM DOME",
        postal_code="1091",
        city="Budapest",
        street="Ulloi",
        street_type="a",
        street_number="133-135",
        tax_number="11111111233",
    )
    assert addr.company_name == "MVM DOME"
    assert addr.tax_number == "11111111233"


def test_receipt_defaults():
    r = Receipt(total="500")
    assert r.receipt_type == "Receipt"
    assert r.is_void is False
    assert r.items == []
    assert r.free_lines == []
    assert r.payments == []


def test_storno_receipt_defaults():
    s = StornoReceipt(total="500")
    assert s.receipt_type == "Void"
    assert s.address is None
    assert s.original_receipt_number == ""
    assert s.date == ""
    assert s.register_id == ""
    assert s.items == []
    assert s.payments == []


def test_receipt_with_items():
    item = ReceiptItem("Item", "Prod", "100", "3", "300", "kg", "2", "0")
    payment = Payment("Cash", "", "Cash", "300")
    r = Receipt(total="300", items=[item], payments=[payment])
    assert len(r.items) == 1
    assert len(r.payments) == 1

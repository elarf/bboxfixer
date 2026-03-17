"""Graphical user interface for bboxfixer.

Allows entering receipt data and generating Windows .bat files
for BBOX fiscal printer reprint and storno operations.
"""

from __future__ import annotations

import os
import sys
import tempfile
import tkinter as tk
from datetime import datetime
from decimal import Decimal, InvalidOperation
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from .generator import BatFileGenerator
from .models import Receipt, ReceiptItem


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAX_RATES = ["27", "18", "5", "0"]
PAYMENT_METHODS = ["cash", "card", "voucher"]
MODES = ["both", "reprint", "storno"]
DEFAULT_HOST = "localhost"
DEFAULT_PORT = "5618"
DEFAULT_STORNO_REASON = "Cancellation"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "bboxfixer_output")

WINDOW_TITLE = "BBoxFixer – Bat File Generator"
WINDOW_MIN_WIDTH = 720
WINDOW_MIN_HEIGHT = 580


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_decimal(value: str) -> Optional[Decimal]:
    """Return a Decimal if value is valid, else None."""
    try:
        return Decimal(value.strip().replace(",", "."))
    except InvalidOperation:
        return None


def _validate_port(value: str) -> Optional[int]:
    try:
        port = int(value.strip())
        if 1 <= port <= 65535:
            return port
    except (ValueError, TypeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Item entry dialog
# ---------------------------------------------------------------------------


class _ItemDialog(tk.Toplevel):
    """Modal dialog for adding / editing a receipt item."""

    def __init__(self, parent: tk.Widget, item: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.title("Add Item" if item is None else "Edit Item")
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[dict] = None

        pad = {"padx": 8, "pady": 4}

        tk.Label(self, text="Name:").grid(row=0, column=0, sticky="e", **pad)
        self._name = tk.StringVar(value=item["name"] if item else "")
        tk.Entry(self, textvariable=self._name, width=28).grid(row=0, column=1, sticky="ew", **pad)

        tk.Label(self, text="Quantity:").grid(row=1, column=0, sticky="e", **pad)
        self._qty = tk.StringVar(value=item["quantity"] if item else "1")
        tk.Entry(self, textvariable=self._qty, width=12).grid(row=1, column=1, sticky="w", **pad)

        tk.Label(self, text="Unit Price:").grid(row=2, column=0, sticky="e", **pad)
        self._price = tk.StringVar(value=item["unit_price"] if item else "0")
        tk.Entry(self, textvariable=self._price, width=12).grid(row=2, column=1, sticky="w", **pad)

        tk.Label(self, text="Tax Rate (%):").grid(row=3, column=0, sticky="e", **pad)
        self._tax = tk.StringVar(value=item["tax_rate"] if item else TAX_RATES[0])
        tax_combo = ttk.Combobox(
            self, textvariable=self._tax, values=TAX_RATES, width=8, state="readonly"
        )
        tax_combo.grid(row=3, column=1, sticky="w", **pad)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame, text="OK", width=10, command=self._ok).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.destroy).pack(side="left", padx=4)

        self.columnconfigure(1, weight=1)
        self._name_entry = self.children.get("!entry")
        # Wait for dialog to close
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def _ok(self) -> None:
        name = self._name.get().strip()
        if not name:
            messagebox.showerror("Validation", "Item name cannot be empty.", parent=self)
            return
        qty = _validate_decimal(self._qty.get())
        if qty is None or qty <= 0:
            messagebox.showerror("Validation", "Quantity must be a positive number.", parent=self)
            return
        price = _validate_decimal(self._price.get())
        if price is None or price < 0:
            messagebox.showerror("Validation", "Unit price must be a non-negative number.", parent=self)
            return
        self.result = {
            "name": name,
            "quantity": str(qty),
            "unit_price": str(price),
            "tax_rate": self._tax.get(),
        }
        self.destroy()


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------


class BBoxFixerApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._items: List[dict] = []
        self._build_ui()
        self._center_window()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        receipt_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook)
        notebook.add(receipt_tab, text="  Receipt Data  ")
        notebook.add(settings_tab, text="  Settings  ")

        self._build_receipt_tab(receipt_tab)
        self._build_settings_tab(settings_tab)
        self._build_bottom_bar()

    def _build_receipt_tab(self, parent: ttk.Frame) -> None:
        pad = {"padx": 8, "pady": 4}

        # ── Header fields ──────────────────────────────────────────────
        hdr = ttk.LabelFrame(parent, text="Receipt Header")
        hdr.pack(fill="x", padx=8, pady=(8, 4))

        fields = [
            ("Receipt Number:", "receipt_number", "R001"),
            ("Date (YYYY-MM-DD):", "date", datetime.today().strftime("%Y-%m-%d")),
            ("Cashier:", "cashier", ""),
        ]
        self._vars: dict[str, tk.StringVar] = {}
        for row_idx, (label, key, default) in enumerate(fields):
            tk.Label(hdr, text=label, anchor="e", width=20).grid(
                row=row_idx, column=0, sticky="e", **pad
            )
            var = tk.StringVar(value=default)
            self._vars[key] = var
            tk.Entry(hdr, textvariable=var, width=30).grid(
                row=row_idx, column=1, sticky="ew", **pad
            )

        tk.Label(hdr, text="Payment Method:", anchor="e", width=20).grid(
            row=len(fields), column=0, sticky="e", **pad
        )
        self._vars["payment_method"] = tk.StringVar(value=PAYMENT_METHODS[0])
        pm_combo = ttk.Combobox(
            hdr,
            textvariable=self._vars["payment_method"],
            values=PAYMENT_METHODS,
            state="readonly",
            width=15,
        )
        pm_combo.grid(row=len(fields), column=1, sticky="w", **pad)
        hdr.columnconfigure(1, weight=1)

        # ── Items table ────────────────────────────────────────────────
        items_frame = ttk.LabelFrame(parent, text="Items")
        items_frame.pack(fill="both", expand=True, padx=8, pady=4)

        cols = ("name", "quantity", "unit_price", "tax_rate", "total")
        self._tree = ttk.Treeview(
            items_frame,
            columns=cols,
            show="headings",
            selectmode="browse",
            height=6,
        )
        col_cfg = [
            ("name", "Name", 200),
            ("quantity", "Qty", 60),
            ("unit_price", "Unit Price", 90),
            ("tax_rate", "Tax %", 60),
            ("total", "Total", 90),
        ]
        for col_id, heading, width in col_cfg:
            self._tree.heading(col_id, text=heading)
            self._tree.column(col_id, width=width, anchor="center")
        self._tree.column("name", anchor="w")

        vsb = ttk.Scrollbar(items_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Buttons
        btn_bar = tk.Frame(parent)
        btn_bar.pack(fill="x", padx=8, pady=(0, 4))
        tk.Button(btn_bar, text="Add Item", width=12, command=self._add_item).pack(side="left", padx=2)
        tk.Button(btn_bar, text="Edit Item", width=12, command=self._edit_item).pack(side="left", padx=2)
        tk.Button(btn_bar, text="Remove Item", width=12, command=self._remove_item).pack(side="left", padx=2)
        tk.Button(btn_bar, text="Clear All", width=10, command=self._clear_items).pack(side="right", padx=2)

        # Total label
        self._total_var = tk.StringVar(value="Total: 0.00")
        tk.Label(parent, textvariable=self._total_var, font=("", 10, "bold")).pack(
            anchor="e", padx=16, pady=2
        )

    def _build_settings_tab(self, parent: ttk.Frame) -> None:
        pad = {"padx": 8, "pady": 5}

        frm = ttk.LabelFrame(parent, text="Printer Connection")
        frm.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(frm, text="Host:", anchor="e", width=16).grid(row=0, column=0, sticky="e", **pad)
        self._vars["host"] = tk.StringVar(value=DEFAULT_HOST)
        tk.Entry(frm, textvariable=self._vars["host"], width=28).grid(row=0, column=1, sticky="ew", **pad)

        tk.Label(frm, text="Port:", anchor="e", width=16).grid(row=1, column=0, sticky="e", **pad)
        self._vars["port"] = tk.StringVar(value=DEFAULT_PORT)
        tk.Entry(frm, textvariable=self._vars["port"], width=10).grid(row=1, column=1, sticky="w", **pad)
        frm.columnconfigure(1, weight=1)

        gen_frm = ttk.LabelFrame(parent, text="Generation Options")
        gen_frm.pack(fill="x", padx=8, pady=4)

        tk.Label(gen_frm, text="Mode:", anchor="e", width=16).grid(row=0, column=0, sticky="e", **pad)
        self._vars["mode"] = tk.StringVar(value=MODES[0])
        mode_combo = ttk.Combobox(
            gen_frm,
            textvariable=self._vars["mode"],
            values=MODES,
            state="readonly",
            width=12,
        )
        mode_combo.grid(row=0, column=1, sticky="w", **pad)

        tk.Label(gen_frm, text="Storno Reason:", anchor="e", width=16).grid(
            row=1, column=0, sticky="e", **pad
        )
        self._vars["storno_reason"] = tk.StringVar(value=DEFAULT_STORNO_REASON)
        tk.Entry(gen_frm, textvariable=self._vars["storno_reason"], width=30).grid(
            row=1, column=1, sticky="ew", **pad
        )

        tk.Label(gen_frm, text="Output Directory:", anchor="e", width=16).grid(
            row=2, column=0, sticky="e", **pad
        )
        self._vars["output_dir"] = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        out_entry = tk.Entry(gen_frm, textvariable=self._vars["output_dir"], width=30)
        out_entry.grid(row=2, column=1, sticky="ew", **pad)
        tk.Button(gen_frm, text="Browse…", command=self._browse_output).grid(row=2, column=2, **pad)
        gen_frm.columnconfigure(1, weight=1)

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self, bd=1, relief="sunken")
        bar.pack(fill="x", side="bottom", padx=0, pady=0)

        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(bar, textvariable=self._status_var, anchor="w", fg="gray40").pack(
            side="left", padx=8, pady=4
        )

        tk.Button(
            bar,
            text="Generate .bat File(s)",
            width=22,
            bg="#2a7bd1",
            fg="white",
            activebackground="#1f63ad",
            activeforeground="white",
            font=("", 10, "bold"),
            command=self._generate,
        ).pack(side="right", padx=8, pady=6)

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    def _add_item(self) -> None:
        dlg = _ItemDialog(self)
        if dlg.result:
            self._items.append(dlg.result)
            self._refresh_tree()

    def _edit_item(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Edit Item", "Please select an item to edit.", parent=self)
            return
        idx = self._tree.index(sel[0])
        dlg = _ItemDialog(self, item=self._items[idx])
        if dlg.result:
            self._items[idx] = dlg.result
            self._refresh_tree()

    def _remove_item(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        self._items.pop(idx)
        self._refresh_tree()

    def _clear_items(self) -> None:
        if self._items and messagebox.askyesno("Clear", "Remove all items?", parent=self):
            self._items.clear()
            self._refresh_tree()

    def _refresh_tree(self) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        running_total = Decimal("0")
        for item in self._items:
            qty = Decimal(item["quantity"])
            price = Decimal(item["unit_price"])
            total = (qty * price).quantize(Decimal("0.01"))
            running_total += total
            self._tree.insert(
                "",
                "end",
                values=(
                    item["name"],
                    item["quantity"],
                    item["unit_price"],
                    item["tax_rate"],
                    f"{total:.2f}",
                ),
            )
        self._total_var.set(f"Total: {running_total:.2f}")

    # ------------------------------------------------------------------
    # Output directory
    # ------------------------------------------------------------------

    def _browse_output(self) -> None:
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self._vars["output_dir"].get() or os.path.expanduser("~"),
        )
        if directory:
            self._vars["output_dir"].set(directory)

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    def _generate(self) -> None:
        # Validate receipt header
        receipt_number = self._vars["receipt_number"].get().strip()
        if not receipt_number:
            messagebox.showerror("Validation", "Receipt Number is required.", parent=self)
            return

        date_str = self._vars["date"].get().strip()
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror(
                "Validation", "Date must be in YYYY-MM-DD format.", parent=self
            )
            return

        cashier = self._vars["cashier"].get().strip()
        if not cashier:
            messagebox.showerror("Validation", "Cashier name is required.", parent=self)
            return

        if not self._items:
            messagebox.showerror("Validation", "Please add at least one item.", parent=self)
            return

        # Validate settings
        host = self._vars["host"].get().strip()
        if not host:
            messagebox.showerror("Validation", "Printer host is required.", parent=self)
            return

        port = _validate_port(self._vars["port"].get())
        if port is None:
            messagebox.showerror("Validation", "Port must be an integer between 1 and 65535.", parent=self)
            return

        output_dir = self._vars["output_dir"].get().strip()
        if not output_dir:
            messagebox.showerror("Validation", "Output directory is required.", parent=self)
            return

        mode = self._vars["mode"].get()
        storno_reason = self._vars["storno_reason"].get().strip() or "Cancellation"

        # Build receipt object
        items = [
            ReceiptItem(
                name=it["name"],
                quantity=Decimal(it["quantity"]),
                unit_price=Decimal(it["unit_price"]),
                tax_rate=Decimal(it["tax_rate"]),
            )
            for it in self._items
        ]
        receipt = Receipt(
            receipt_number=receipt_number,
            date=date,
            cashier=cashier,
            payment_method=self._vars["payment_method"].get(),
            items=items,
        )

        # Generate bat files
        try:
            os.makedirs(output_dir, exist_ok=True)
            gen = BatFileGenerator(host=host, port=port, output_dir=output_dir)
            paths = gen.generate_all([receipt], mode=mode, storno_reason=storno_reason)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to generate bat files:\n{exc}", parent=self)
            return

        summary = "\n".join(f"  • {os.path.basename(p)}" for p in paths)
        self._status_var.set(f"Generated {len(paths)} file(s) in {output_dir}")
        messagebox.showinfo(
            "Success",
            f"Generated {len(paths)} bat file(s) in:\n{output_dir}\n\n{summary}",
            parent=self,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _center_window(self) -> None:
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), WINDOW_MIN_WIDTH)
        h = max(self.winfo_reqheight(), WINDOW_MIN_HEIGHT)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    app = BBoxFixerApp()
    app.mainloop()


if __name__ == "__main__":
    main()

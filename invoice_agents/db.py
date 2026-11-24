"""SQLite store: inventory catalog, known vendors, the invoice ledger and the payment log."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(os.environ.get("INVOICE_DB", "inventory.db"))

INVENTORY = [("WidgetA", 15, 250.0), ("WidgetB", 10, 500.0), ("GadgetX", 5, 750.0), ("FakeItem", 0, None)]

VENDORS = [
    ("Widgets Inc.", [], "2023-03-01"),
    ("Gadgets Co.", [], "2023-06-12"),
    ("Precision Parts Ltd.", [], "2024-01-08"),
    ("Global Supply Chain Partners", [], "2024-02-19"),
    ("Acme Industrial Supplies", [], "2022-11-30"),
    ("MegaWidgets Corp", [], "2024-05-02"),
    ("Consolidated Materials Group", [], "2023-09-14"),
    ("Summit Manufacturing Co.", [], "2023-04-22"),
    ("QuickShip Distributers", ["FastShip Ltd."], "2021-07-01"),
    ("Atlas Industrial Supply", [], "2024-08-09"),
    ("TechParts International", [], "2025-01-15"),
    ("Reliable Components Inc.", [], "2022-03-27"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock INTEGER, unit_price REAL);
CREATE TABLE IF NOT EXISTS vendors (name TEXT PRIMARY KEY, aliases TEXT NOT NULL, first_seen TEXT);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT, number_key TEXT, vendor TEXT, vendor_key TEXT, content_hash TEXT,
    status TEXT NOT NULL, disposition TEXT, total REAL, currency TEXT,
    source_file TEXT, run_id TEXT, processed_at TEXT, lines TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    idempotency_key TEXT PRIMARY KEY, invoice_number TEXT, vendor TEXT, amount REAL,
    status TEXT NOT NULL, attempts INTEGER NOT NULL, updated_at TEXT
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    """One SQLite file holding everything the agents look up or write. Created and seeded on first open."""

    def __init__(self, path: Path = DEFAULT_DB):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        if not self.conn.execute("SELECT 1 FROM inventory").fetchone():
            self._seed()

    def _seed(self) -> None:
        self.conn.executemany("INSERT INTO inventory VALUES (?, ?, ?)", INVENTORY)
        self.conn.executemany(
            "INSERT INTO vendors VALUES (?, ?, ?)", [(n, json.dumps(a), s) for n, a, s in VENDORS]
        )
        self.conn.commit()

    def reset(self) -> None:
        """Drop every table and reseed: empty ledger, no payments."""
        self.conn.executescript(
            "DROP TABLE IF EXISTS inventory; DROP TABLE IF EXISTS vendors;"
            "DROP TABLE IF EXISTS invoices; DROP TABLE IF EXISTS payments;"
        )
        self.conn.executescript(SCHEMA)
        self._seed()

    def catalog(self) -> dict[str, dict[str, Any]]:
        """Inventory rows keyed by item name."""
        rows = self.conn.execute("SELECT item, stock, unit_price FROM inventory").fetchall()
        return {r["item"]: dict(r) for r in rows}

    def vendors(self) -> list[dict[str, Any]]:
        """Known vendors with their aliases."""
        rows = self.conn.execute("SELECT name, aliases, first_seen FROM vendors").fetchall()
        return [{**dict(r), "aliases": json.loads(r["aliases"])} for r in rows]

    def related_invoices(self, number_key: str, vendor_key: str, content_hash: str) -> list[dict[str, Any]]:
        """Ledger rows sharing this invoice's number, vendor or content, oldest first."""
        rows = self.conn.execute(
            "SELECT * FROM invoices WHERE number_key = ? OR vendor_key = ? OR content_hash = ? ORDER BY id",
            (number_key, vendor_key, content_hash),
        ).fetchall()
        return [{**dict(r), "lines": json.loads(r["lines"] or "[]")} for r in rows]

    def record_invoice(self, **row: Any) -> None:
        """Append one processed invoice to the ledger."""
        row = {**row, "lines": json.dumps(row.get("lines", [])), "processed_at": _now()}
        cols = ", ".join(row)
        self.conn.execute(f"INSERT INTO invoices ({cols}) VALUES ({', '.join('?' * len(row))})", list(row.values()))
        self.conn.commit()

    def ledger(self) -> list[dict[str, Any]]:
        """Every processed invoice, newest first."""
        rows = self.conn.execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def payment(self, key: str) -> dict[str, Any] | None:
        """The payment row for an idempotency key, if any."""
        row = self.conn.execute("SELECT * FROM payments WHERE idempotency_key = ?", (key,)).fetchone()
        return dict(row) if row else None

    def save_payment(self, key: str, invoice_number: str, vendor: str, amount: float, status: str, attempts: int):
        """Insert or update the payment row for an idempotency key and commit at once."""
        self.conn.execute(
            "INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(idempotency_key) DO UPDATE SET "
            "status = excluded.status, attempts = excluded.attempts, updated_at = excluded.updated_at",
            (key, invoice_number, vendor, amount, status, attempts, _now()),
        )
        self.conn.commit()

    def payments(self) -> list[dict[str, Any]]:
        """Every payment row."""
        return [dict(r) for r in self.conn.execute("SELECT * FROM payments ORDER BY updated_at").fetchall()]

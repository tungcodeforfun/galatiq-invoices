"""Data model shared by every stage: the extracted invoice, findings, agent outputs and the outcome."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Correction(BaseModel):
    """A value the intake agent normalized, kept beside what the document actually said."""

    field: str = Field(description="Which field was corrected, e.g. 'invoice_date' or 'line_items[1].amount'")
    as_written: str = Field(description="The text exactly as it appears in the document")
    normalized: str = Field(description="The value used after correction")


class LineItem(BaseModel):
    """One line of an invoice as extracted, before any catalog matching."""

    description: str = Field(description="Item name or description exactly as written on the line")
    quantity: float | None = Field(description="Quantity as written, negative if written negative; null if absent")
    unit_price: float | None = Field(description="Unit price as a plain number; null if absent")
    amount: float | None = Field(description="Line total as written on the document; null if the line shows none")
    note: str | None = Field(description="Any note printed on this line, e.g. 'Volume discount'; null if none")


class Invoice(BaseModel):
    """Structured invoice produced by the intake stage. Missing values stay null; nothing is invented."""

    invoice_number: str | None = Field(description="Invoice number as written, e.g. 'INV-1001' or '1002'")
    vendor: str | None = Field(description="Name of the vendor issuing the invoice; null if blank or missing")
    invoice_date: str | None = Field(description="Invoice date as YYYY-MM-DD; null if missing or not a date")
    due_date: str | None = Field(description="Due date as YYYY-MM-DD; null if missing or not a calendar date")
    due_date_as_written: str | None = Field(description="The due date text exactly as written; null if absent")
    currency: str | None = Field(description="ISO currency code if the document states one or uses a symbol")
    line_items: list[LineItem]
    subtotal: float | None = Field(description="Subtotal as written; null if the document shows none")
    tax: float | None = Field(description="Tax amount as written; null if the document shows none")
    shipping: float | None = Field(description="Shipping or freight charge as written; null if none")
    total: float | None = Field(description="Total amount due as written on the document")
    payment_terms: str | None = Field(description="Payment terms as written, e.g. 'Net 30'")
    notes: str | None = Field(description="All free text: notes, messages, remittance or bank instructions")
    revision: str | None = Field(description="Revision marker if the document says it is revised, e.g. 'R1'")
    corrections: list[Correction] = Field(
        description="Every value you changed from how it was written (typos, OCR letters in numbers, dates)"
    )


class Severity(StrEnum):
    """How a finding affects the outcome."""

    REJECT = "reject"
    WARN = "warn"
    INFO = "info"


class Finding(BaseModel):
    """A fact established by code or a cited judgment by an agent, with the evidence behind it."""

    id: str = ""
    code: str
    severity: Severity
    message: str
    subject: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    source: str


class Signal(BaseModel):
    """One fraud or risk signal, quoted verbatim from the invoice."""

    kind: Literal[
        "pressure_language",
        "payment_redirect",
        "instruction_injection",
        "vendor_change",
        "unusual_terms",
        "other",
    ]
    quote: str = Field(description="Exact text copied from the invoice document that shows the signal")
    why: str = Field(description="One sentence on why this matters for paying the invoice")


class RiskMemo(BaseModel):
    """The risk analyst's read of the invoice."""

    level: Literal["low", "medium", "high"]
    signals: list[Signal]
    summary: str = Field(description="Two sentences at most for the VP")


class Reason(BaseModel):
    """One reason in an approval decision, tied to the findings it rests on."""

    text: str
    finding_ids: list[str] = Field(description="IDs of the findings this reason relies on, e.g. ['F1']")


class Decision(BaseModel):
    """The VP approver's decision."""

    action: Literal["approve", "reject"]
    reasons: list[Reason]
    addressed_findings: list[str] = Field(description="IDs of every finding this decision has considered")
    summary: str = Field(description="One or two sentences a finance manager would read")


class Critique(BaseModel):
    """The critic's review of a VP draft."""

    verdict: Literal["accept", "revise"]
    objections: list[str] = Field(description="Specific problems with the draft; empty when the verdict is accept")


Disposition = Literal["return_to_vendor", "void"]


class Resolution(BaseModel):
    """What happens to a rejected invoice and what the vendor is told."""

    disposition: Disposition
    reasoning: str = Field(description="Why the invoice was rejected, for the audit log")
    vendor_reply: str | None = Field(description="Email to the vendor saying what to fix; null when voided")


class Payment(BaseModel):
    """Result of the payment stage."""

    status: Literal["success", "failed", "already_paid", "blocked"]
    idempotency_key: str
    amount: float
    attempts: int
    detail: str = ""


class Outcome(BaseModel):
    """Where an invoice ended up."""

    status: Literal["PAID", "REJECTED", "PAYMENT_FAILED"]
    disposition: Disposition | None = None
    amount: float | None = None
    summary: str

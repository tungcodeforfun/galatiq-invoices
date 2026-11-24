"""Turns any invoice file into text. One path for every format: PDFs through pdfplumber, everything else as text."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pdfplumber


class UnreadableDocument(Exception):
    """The file could not be turned into text."""


def read_document(path: Path) -> str:
    """Text of an invoice file; the format is left for the intake agent to interpret."""
    try:
        if path.suffix.lower() == ".pdf":
            with pdfplumber.open(path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise UnreadableDocument(f"{path.name}: {exc}") from exc
    if not text.strip():
        raise UnreadableDocument(f"{path.name}: no text found")
    return text


def file_digest(path: Path) -> str:
    """Short SHA-256 of the file bytes, for the audit log."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

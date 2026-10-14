"""PDF upload adapter (text PDFs via pdfplumber; OCR for scans is a roadmap item)."""

from datetime import datetime
from pathlib import Path

import pdfplumber

from brain.messages import Message


def from_pdf(path: Path, raw_path: str = "", received_at: datetime | None = None) -> Message:
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        created = str(pdf.metadata.get("CreationDate", ""))
    if received_at is None:
        try:  # PDF date format: D:YYYYMMDDHHmmSS...
            received_at = datetime.strptime(created.removeprefix("D:")[:14], "%Y%m%d%H%M%S")
        except ValueError:
            received_at = datetime.fromtimestamp(Path(path).stat().st_mtime)
    return Message("pdf", "upload", Path(path).name, text, received_at, raw_path or str(path))

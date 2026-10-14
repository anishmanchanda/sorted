"""One internal message format for every source (email, SMS, PDF, chat, web)."""

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from brain.redact import redact

IST = ZoneInfo("Asia/Kolkata")


def to_ist_naive(dt: datetime) -> datetime:
    return dt.astimezone(IST).replace(tzinfo=None) if dt.tzinfo else dt


def sender_key(kind: str, sender: str) -> str:
    """Stable grouping key: email domain, SMS header without operator prefix (VM-HDFCBK -> HDFCBK)."""
    if kind == "email":
        return parseaddr(sender)[1].rsplit("@", 1)[-1].lower()
    if kind == "sms":
        return sender.rsplit("-", 1)[-1].upper()
    return kind


@dataclass
class Message:
    kind: str  # email / sms / pdf / chat / web
    sender: str
    subject: str
    body: str
    received_at: datetime  # naive, IST
    raw_path: str = ""

    @property
    def sender_key(self) -> str:
        return sender_key(self.kind, self.sender)

    @property
    def body_hash(self) -> str:
        return hashlib.sha256(f"{self.kind}|{self.sender}|{self.subject}|{self.body}".encode()).hexdigest()

    def redacted_text(self) -> str:
        """What agents, compiled abilities and the compiler see. The sender (a biller) is kept for context."""
        return (
            f"From: {self.sender}\nSubject: {redact(self.subject)}\nDate: {self.received_at:%Y-%m-%d %H:%M}\n\n"
            f"{redact(self.body.strip())}\n"
        )


class _HTMLText(HTMLParser):
    BLOCK = {"p", "br", "tr", "div", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")
        elif tag in ("td", "th", "span"):
            self.out.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(html: str) -> str:
    p = _HTMLText()
    p.feed(html)
    lines = (re.sub(r"[ \t\xa0]+", " ", line).strip() for line in "".join(p.out).splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def pdf_bytes_to_text(data: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def from_eml(data: bytes, raw_path: str = "") -> Message:
    msg = BytesParser(policy=policy.default).parsebytes(data)
    part = msg.get_body(preferencelist=("html", "plain"))
    content = part.get_content() if part else ""
    body = html_to_text(content) if part is not None and part.get_content_subtype() == "html" else content
    for att in msg.iter_attachments():
        ctype, name = att.get_content_type(), att.get_filename() or "attachment"
        if ctype == "text/calendar":
            body += f"\n\n[attachment {name}]\n{att.get_content()}"
        elif ctype == "application/pdf":
            body += f"\n\n[attachment {name}]\n{pdf_bytes_to_text(att.get_content())}"
    received = parsedate_to_datetime(msg["Date"]) if msg["Date"] else datetime.now(IST)
    return Message("email", str(msg["From"] or ""), str(msg["Subject"] or ""), body, to_ist_naive(received), raw_path)

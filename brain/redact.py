"""Mask personal identifiers before any text leaves the machine (and before abilities see it, so both agree)."""

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# UPI IDs (name@okhdfcbank, 9876543210@ybl): like an email but the handle has no dot, so _EMAIL misses them.
_UPI = re.compile(r"(?<![\w.+-])[\w.-]{2,}@[a-z]{2,30}\b(?!\.\w)", re.I)
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")  # 13-19 digits, optional single space/dash separators
_PHONE = re.compile(r"(?<![\d.,])(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d|[.,]\d)")
_ACCOUNT = re.compile(r"(?<![\d/.,])\d{9,18}(?!\d|[/.,]\d)")  # account / policy / consumer numbers


def _last4(s: str) -> str:
    return re.sub(r"\D", "", s)[-4:]


def redact(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _UPI.sub("[upi]", text)  # before _PHONE, so "9876543210@ybl" is masked whole
    text = _CARD.sub(lambda m: "XXXX XXXX XXXX " + _last4(m.group()), text)
    text = _PHONE.sub("[phone]", text)
    return _ACCOUNT.sub(lambda m: "X" * (len(m.group()) - 4) + m.group()[-4:], text)

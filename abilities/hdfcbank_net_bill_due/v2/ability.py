"""Ability hdfcbank_net_bill_due v2: compiled by Sorted from 5 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'hdfcbank.net', 'type': 'bill_due', 'subject_keywords': ['bank', 'card', 'credit', 'hdfc', 'statement']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime
from decimal import Decimal
from dateutil import parser as dateparser


def extract(text: str) -> dict:
    def must_search(pattern, src, flags=0):
        m = re.search(pattern, src, flags)
        if not m:
            raise ValueError("Required label missing")
        return m

    def parse_amount(raw):
        cleaned = raw.replace(",", "").strip()
        return float(Decimal(cleaned))

    def parse_date(raw):
        raw = raw.strip()
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", raw):
            return datetime.strptime(raw, "%d/%m/%Y").strftime("%Y-%m-%d")
        dt = dateparser.parse(raw, dayfirst=True)
        if not dt:
            raise ValueError("Required label missing")
        return dt.strftime("%Y-%m-%d")

    amount = None
    due_date = None

    m_amount = re.search(r"Total\s+Amount\s+Due\s+Rs\.?\s*([\d,]+(?:\.\d{2})?)", text, re.I)
    if m_amount:
        amount = parse_amount(m_amount.group(1))
    else:
        m_amount = re.search(r"Amount\s+payable\s+INR\s*([\d,]+(?:\.\d{2})?)", text, re.I)
        if m_amount:
            amount = parse_amount(m_amount.group(1))
        else:
            raise ValueError("Required label missing")

    m_due = re.search(r"Payment\s+Due\s+Date\s*(\d{2}/\d{2}/\d{4})", text, re.I)
    if m_due:
        due_date = parse_date(m_due.group(1))
    else:
        m_due = re.search(r"Pay\s+by\s+([0-3]?\d\s+[A-Za-z]{3,9}\s+\d{4})", text, re.I)
        if m_due:
            due_date = parse_date(m_due.group(1))
        else:
            raise ValueError("Required label missing")

    return {
        "type": "bill_due",
        "provider": "HDFC Bank",
        "amount": amount,
        "currency": "INR",
        "due_date": due_date,
    }

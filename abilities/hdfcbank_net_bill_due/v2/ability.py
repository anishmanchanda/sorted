"""Ability hdfcbank_net_bill_due v2: compiled by Sorted from 5 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'hdfcbank.net', 'type': 'bill_due', 'subject_keywords': ['bank', 'card', 'credit', 'hdfc', 'statement']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    def parse_amount(value: str) -> float:
        cleaned = value.replace(',', '').strip()
        return float(cleaned)

    def parse_date(value: str) -> str:
        value = value.strip()
        for fmt in ('%d/%m/%Y', '%d %b %Y', '%d %B %Y'):
            try:
                return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
            except ValueError:
                pass
        raise ValueError('Unable to parse date')

    amount_match = re.search(
        r'(?im)^\s*Total\s+Amount\s+Due\s+Rs\.\s*([\d,]+(?:\.\d{2})?)\s*$',
        text,
    )
    due_match = re.search(
        r'(?im)^\s*Payment\s+Due\s+Date\s+(\d{2}/\d{2}/\d{4})\s*$',
        text,
    )

    if amount_match and due_match:
        amount = parse_amount(amount_match.group(1))
        due_date = parse_date(due_match.group(1))
        return {
            'type': 'bill_due',
            'provider': 'HDFC Bank',
            'amount': amount,
            'currency': 'INR',
            'due_date': due_date,
        }

    amount_match = re.search(
        r'(?im)^\s*Amount\s+payable\s+INR\s*([\d,]+(?:\.\d{2})?)\s*$',
        text,
    )
    due_match = re.search(
        r'(?im)^\s*Pay\s+by\s+([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})\s*$',
        text,
    )

    if amount_match and due_match:
        amount = parse_amount(amount_match.group(1))
        due_date = parse_date(due_match.group(1))
        return {
            'type': 'bill_due',
            'provider': 'HDFC Bank',
            'amount': amount,
            'currency': 'INR',
            'due_date': due_date,
        }

    has_old_layout = re.search(r'(?im)^\s*Total\s+Amount\s+Due\b', text) or re.search(r'(?im)^\s*Payment\s+Due\s+Date\b', text)
    has_new_layout = re.search(r'(?im)^\s*Amount\s+payable\b', text) or re.search(r'(?im)^\s*Pay\s+by\b', text)

    if has_old_layout or has_new_layout:
        raise ValueError('Required label missing or malformed')

    raise ValueError('Required labels not found')

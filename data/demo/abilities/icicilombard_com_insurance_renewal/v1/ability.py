"""Ability icicilombard_com_insurance_renewal v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'icicilombard.com', 'type': 'insurance_renewal', 'subject_keywords': ['expires', 'insurance', 'policy', 'renew']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def _parse_amount(amount_text: str) -> float:
    cleaned = amount_text.strip()
    cleaned = cleaned.replace(',', '')
    return float(cleaned)


def _parse_date(date_text: str) -> str:
    dt = datetime.strptime(date_text.strip(), '%d %b %Y')
    return dt.strftime('%Y-%m-%d')


def extract(text: str) -> dict:
    if not re.search(r'ICICI\s+Lombard', text, re.IGNORECASE):
        raise ValueError('Missing provider label')

    amount_match = re.search(
        r'Renewal\s+premium\s*:\s*₹\s*([0-9][0-9,]*\.\d{2})',
        text,
        re.IGNORECASE,
    )
    if not amount_match:
        raise ValueError('Missing renewal premium label')

    due_date_match = re.search(
        r'expires\s+on\s+([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})',
        text,
        re.IGNORECASE,
    )
    if not due_date_match:
        raise ValueError('Missing expiry date label')

    return {
        'type': 'insurance_renewal',
        'provider': 'ICICI Lombard',
        'amount': _parse_amount(amount_match.group(1)),
        'currency': 'INR',
        'due_date': _parse_date(due_date_match.group(1)),
    }

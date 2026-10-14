"""Ability airtel_com_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'airtel.com', 'type': 'bill_due', 'subject_keywords': ['airtel', 'bill', 'fiber', 'xstream']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def _parse_amount(value: str) -> float:
    cleaned = value.strip()
    cleaned = cleaned.replace('₹', '').replace('Rs.', '').replace('Rs', '')
    cleaned = cleaned.replace(',', '').strip()
    return float(cleaned)


def _parse_date(value: str) -> str:
    return datetime.strptime(value.strip(), '%d-%b-%Y').strftime('%Y-%m-%d')


def extract(text: str) -> dict:
    amount_match = re.search(r'(?im)^\s*Amount\s+due\s*:\s*([^\n\r]+)', text)
    if not amount_match:
        raise ValueError('Missing Amount due label')

    due_date_match = re.search(r'(?im)^\s*Due\s+date\s*:\s*([^\n\r]+)', text)
    if not due_date_match:
        raise ValueError('Missing Due date label')

    amount = _parse_amount(amount_match.group(1))
    due_date = _parse_date(due_date_match.group(1))

    return {
        'type': 'bill_due',
        'provider': 'Airtel',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
    }

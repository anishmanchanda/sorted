"""Ability hdfcbank_net_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'hdfcbank.net', 'type': 'bill_due', 'subject_keywords': ['bank', 'card', 'credit', 'hdfc', 'statement']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    due_match = re.search(r'Payment\s+Due\s+Date\s+([0-3]?\d/[01]?\d/\d{4})', text, re.IGNORECASE)
    if not due_match:
        raise ValueError('Missing Payment Due Date label')

    amount_match = re.search(r'Total\s+Amount\s+Due\s+Rs\.\s*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
    if not amount_match:
        raise ValueError('Missing Total Amount Due label')

    due_date_raw = due_match.group(1).strip()
    amount_raw = amount_match.group(1).replace(',', '').strip()

    try:
        due_date = datetime.strptime(due_date_raw, '%d/%m/%Y').strftime('%Y-%m-%d')
    except Exception:
        raise ValueError('Invalid due date format')

    try:
        amount = float(amount_raw)
    except Exception:
        raise ValueError('Invalid amount format')

    return {
        'type': 'bill_due',
        'provider': 'HDFC Bank',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
    }

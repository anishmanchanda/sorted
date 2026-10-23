"""Ability hdfcbank_net_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'hdfcbank.net', 'type': 'bill_due', 'subject_keywords': ['bank', 'card', 'credit', 'hdfc', 'statement']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    amt_match = re.search(r'Total\s+Amount\s+Due\s+Rs\.\s*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
    if not amt_match:
        raise ValueError('Missing Total Amount Due label')

    due_match = re.search(r'Payment\s+Due\s+Date\s+([0-3]?\d/[0-1]?\d/\d{4})', text, re.IGNORECASE)
    if not due_match:
        raise ValueError('Missing Payment Due Date label')

    amount = float(amt_match.group(1).replace(',', ''))
    due_date = datetime.strptime(due_match.group(1), '%d/%m/%Y').strftime('%Y-%m-%d')

    return {
        'type': 'bill_due',
        'provider': 'HDFC Bank',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
    }

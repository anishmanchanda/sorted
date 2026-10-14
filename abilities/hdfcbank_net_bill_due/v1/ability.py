"""Ability hdfcbank_net_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'hdfcbank.net', 'type': 'bill_due', 'subject_keywords': ['bank', 'card', 'credit', 'hdfc', 'statement']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    due_date_match = re.search(r'(?im)^\s*Payment\s+Due\s+Date\s+([0-9]{2}/[0-9]{2}/[0-9]{4})\s*$', text)
    if not due_date_match:
        raise ValueError('Missing Payment Due Date')

    amount_match = re.search(r'(?im)^\s*Total\s+Amount\s+Due\s+Rs\.\s*([0-9][0-9,]*\.\d{2})\s*$', text)
    if not amount_match:
        raise ValueError('Missing Total Amount Due')

    due_date = datetime.strptime(due_date_match.group(1), '%d/%m/%Y').strftime('%Y-%m-%d')
    amount = float(amount_match.group(1).replace(',', ''))

    return {
        'type': 'bill_due',
        'provider': 'HDFC Bank',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
    }

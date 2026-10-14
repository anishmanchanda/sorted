"""Ability bsesdelhi_com_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'bsesdelhi.com', 'type': 'bill_due', 'subject_keywords': ['bill', 'bses', 'electricity', 'rajdhani']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    amount_match = re.search(r'Net\s+Amount\s+Payable\s*\(Rs\.\)\s*([0-9][0-9,]*\.\d{2})', text, re.IGNORECASE)
    if not amount_match:
        raise ValueError('Missing Net Amount Payable label')

    due_match = re.search(r'Due\s+Date\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})', text, re.IGNORECASE)
    if not due_match:
        raise ValueError('Missing Due Date label')

    amount = float(amount_match.group(1).replace(',', ''))
    due_date = datetime.strptime(due_match.group(1), '%d.%m.%Y').strftime('%Y-%m-%d')

    return {
        'type': 'bill_due',
        'provider': 'BSES Rajdhani',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
    }

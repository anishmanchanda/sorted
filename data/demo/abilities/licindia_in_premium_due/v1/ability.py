"""Ability licindia_in_premium_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'licindia.in', 'type': 'premium_due', 'subject_keywords': ['notice', 'policy', 'premium']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime
from decimal import Decimal


def extract(text: str) -> dict:
    amt_match = re.search(r'(?im)^\s*Premium\s+Amount\s*:\s*(?:Rs\.?|INR)\s*([0-9][0-9,]*\.\d{2})\s*$', text)
    if not amt_match:
        raise ValueError('Missing Premium Amount label')

    due_match = re.search(r'(?im)^\s*Due\s+Date\s*:\s*([0-3]?\d/[0-1]?\d/\d{4})\s*$', text)
    if not due_match:
        raise ValueError('Missing Due Date label')

    amount_str = amt_match.group(1).replace(',', '')
    amount = float(Decimal(amount_str))

    try:
        due_date = datetime.strptime(due_match.group(1), '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError('Invalid Due Date format')

    return {
        'type': 'premium_due',
        'provider': 'LIC',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
    }

"""Ability licindia_in_premium_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'licindia.in', 'type': 'premium_due', 'subject_keywords': ['notice', 'policy', 'premium']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    if not re.search(r'^\s*PREMIUM\s+DUE\s+NOTICE\s*$', text, re.IGNORECASE | re.MULTILINE):
        raise ValueError('Missing PREMIUM DUE NOTICE label')

    amount_match = re.search(
        r'^\s*Premium\s+Amount\s*:\s*Rs\.\s*([0-9][0-9,]*\.\d{2})\s*$',
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not amount_match:
        raise ValueError('Missing Premium Amount label')

    due_date_match = re.search(
        r'^\s*Due\s+Date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})\s*$',
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not due_date_match:
        raise ValueError('Missing Due Date label')

    amount = float(amount_match.group(1).replace(',', ''))
    due_date = datetime.strptime(due_date_match.group(1), '%d/%m/%Y').strftime('%Y-%m-%d')

    provider = 'LIC of India'

    return {
        'type': 'premium_due',
        'provider': provider,
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
    }

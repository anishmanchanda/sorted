"""Ability icicilombard_com_insurance_renewal v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'icicilombard.com', 'type': 'insurance_renewal', 'subject_keywords': ['expires', 'insurance', 'policy', 'renew']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    subject_match = re.search(r'^Subject:\s*(.+)$', text, re.MULTILINE)
    if not subject_match:
        raise ValueError('Missing Subject header')

    amount_match = re.search(r'Renewal\s+premium\s*:\s*₹\s*([0-9][0-9,]*\.?[0-9]*)', text, re.IGNORECASE)
    if not amount_match:
        raise ValueError('Missing Renewal premium label')

    due_match = re.search(r'expires\s+on\s+([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})', text, re.IGNORECASE)
    if not due_match:
        raise ValueError('Missing expires on label')

    amount = float(amount_match.group(1).replace(',', ''))
    due_date = datetime.strptime(due_match.group(1), '%d %b %Y').strftime('%Y-%m-%d')

    return {
        'type': 'insurance_renewal',
        'provider': 'ICICI Lombard',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
    }

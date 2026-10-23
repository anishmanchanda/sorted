"""Ability account_netflix_com_subscription_receipt v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'account.netflix.com', 'type': 'subscription_receipt', 'subject_keywords': ['netflix', 'payment', 'receipt']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date', 'service']

import re
from datetime import datetime

def extract(text: str) -> dict:
    amount_match = re.search(r'(?mi)^\s*Amount\s*₹\s*([0-9][0-9,]*\.\d{2})\s*$', text)
    if not amount_match:
        raise ValueError('Missing Amount label')
    amount = float(amount_match.group(1).replace(',', ''))

    due_match = re.search(r'(?mi)^\s*Next\s+billing\s+date\s+([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})\s*$', text)
    if not due_match:
        raise ValueError('Missing Next billing date label')
    due_date = datetime.strptime(due_match.group(1).strip(), '%d %B %Y').strftime('%Y-%m-%d')

    return {
        'type': 'subscription_receipt',
        'provider': 'Netflix',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date,
        'service': 'Netflix',
    }

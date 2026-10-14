"""Ability hdfcbank_net_bill_due v2: compiled by Sorted from 5 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'hdfcbank.net', 'type': 'bill_due', 'subject_keywords': ['bank', 'card', 'credit', 'hdfc', 'statement']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime
from dateutil import parser as date_parser


def extract(text: str) -> dict:
    def parse_amount(value: str) -> float:
        cleaned = value.replace(',', '').strip()
        return float(cleaned)

    def parse_date(value: str) -> str:
        value = value.strip()
        for fmt in ('%d/%m/%Y', '%d-%b-%Y', '%d %b %Y'):
            try:
                return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
            except ValueError:
                pass
        try:
            return date_parser.parse(value, dayfirst=True).date().isoformat()
        except Exception:
            raise ValueError('Unable to parse date')

    amount_match = re.search(r'(?im)^\s*Total\s+Amount\s+Due\s+Rs\.\s*([0-9][0-9,]*\.\d{2})\s*$', text)
    if not amount_match:
        amount_match = re.search(r'(?im)^\s*Amount\s+payable\s+INR\s*([0-9][0-9,]*\.\d{2})\s*$', text)
    if not amount_match:
        raise ValueError('Missing amount label')

    due_match = re.search(r'(?im)^\s*Payment\s+Due\s+Date\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})\s*$', text)
    if not due_match:
        due_match = re.search(r'(?im)^\s*Pay\s+by\s+([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})\s*$', text)
    if not due_match:
        raise ValueError('Missing due date label')

    return {
        'type': 'bill_due',
        'provider': 'HDFC Bank',
        'amount': parse_amount(amount_match.group(1)),
        'currency': 'INR',
        'due_date': parse_date(due_match.group(1)),
    }

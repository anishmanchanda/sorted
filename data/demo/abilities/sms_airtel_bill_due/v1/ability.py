"""Ability sms_airtel_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'sms', 'sender_key': 'AIRTEL', 'type': 'bill_due', 'subject_keywords': []}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    amount_match = re.search(r"\bAirtel\s+Xstream\s+bill\s+of\s+Rs\s*([\d,]+(?:\.\d+)?)\b", text, re.IGNORECASE)
    if not amount_match:
        raise ValueError("Missing Airtel Xstream bill amount label")

    due_match = re.search(r"\bis\s+due\s+on\s+(\d{1,2}-[A-Za-z]{3}-\d{4})\b", text, re.IGNORECASE)
    if not due_match:
        raise ValueError("Missing due date label")

    amount = float(amount_match.group(1).replace(',', ''))
    due_date = datetime.strptime(due_match.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")

    return {
        "type": "bill_due",
        "provider": "Airtel",
        "amount": amount,
        "currency": "INR",
        "due_date": due_date,
    }

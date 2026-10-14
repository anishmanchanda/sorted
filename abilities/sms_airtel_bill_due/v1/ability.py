"""Ability sms_airtel_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'sms', 'sender_key': 'AIRTEL', 'type': 'bill_due', 'subject_keywords': []}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    if not isinstance(text, str):
        raise ValueError("text must be a string")

    pattern = re.compile(
        r"Airtel\s+Xstream\s+bill\s+of\s+Rs\s*([0-9,]+(?:\.[0-9]+)?)\s+for\s+a/c\s+\S+\s+is\s+due\s+on\s+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError("Required Airtel bill due labels not found")

    amount_str = match.group(1).replace(",", "")
    due_date_str = match.group(2)

    try:
        amount = float(amount_str)
    except Exception:
        raise ValueError("Invalid amount format")

    try:
        due_date = datetime.strptime(due_date_str, "%d-%b-%Y").strftime("%Y-%m-%d")
    except Exception:
        raise ValueError("Invalid due date format")

    return {
        "type": "bill_due",
        "provider": "Airtel",
        "amount": amount,
        "currency": "INR",
        "due_date": due_date,
    }

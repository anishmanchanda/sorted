"""Ability sms_hdfcbk_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'sms', 'sender_key': 'HDFCBK', 'type': 'bill_due', 'subject_keywords': []}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    total_match = re.search(r"Total\s+due\s*:\s*Rs\.\s*([0-9][0-9,]*\.\d{2})", text, re.IGNORECASE)
    if not total_match:
        raise ValueError("Missing Total due label")

    due_date_match = re.search(r"Due\s+date\s*:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{2,4})", text, re.IGNORECASE)
    if not due_date_match:
        raise ValueError("Missing Due date label")

    amount = float(total_match.group(1).replace(",", ""))

    raw_date = due_date_match.group(1)
    try:
        due_date = datetime.strptime(raw_date, "%d-%b-%y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            due_date = datetime.strptime(raw_date, "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid due date format")

    return {
        "type": "bill_due",
        "provider": "HDFC Bank",
        "amount": amount,
        "currency": "INR",
        "due_date": due_date,
    }

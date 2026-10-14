"""Ability airtel_com_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'airtel.com', 'type': 'bill_due', 'subject_keywords': ['airtel', 'bill', 'fiber', 'xstream']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    amount_match = re.search(r"Amount\s*due\s*:\s*[₹Rs\.\s]*([0-9][0-9,]*\.\d{2})", text, re.IGNORECASE)
    if not amount_match:
        raise ValueError("Missing Amount due label")

    due_match = re.search(r"Due\s*date\s*:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})", text, re.IGNORECASE)
    if not due_match:
        raise ValueError("Missing Due date label")

    amount = float(amount_match.group(1).replace(",", ""))
    due_date = datetime.strptime(due_match.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")

    return {
        "type": "bill_due",
        "provider": "Airtel Xstream Fiber",
        "amount": amount,
        "currency": "INR",
        "due_date": due_date,
    }

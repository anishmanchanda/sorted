"""Ability sms_hdfcbk_bill_due v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'sms', 'sender_key': 'HDFCBK', 'type': 'bill_due', 'subject_keywords': []}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    m_amount = re.search(r"Total\s+due\s*:\s*Rs\.?\s*([0-9][0-9,]*\.?[0-9]{0,2})", text, re.IGNORECASE)
    if not m_amount:
        raise ValueError("Missing Total due label")

    m_due = re.search(r"Due\s+date\s*:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{2})", text, re.IGNORECASE)
    if not m_due:
        raise ValueError("Missing Due date label")

    amount = float(m_amount.group(1).replace(",", ""))
    due_date = datetime.strptime(m_due.group(1), "%d-%b-%y").strftime("%Y-%m-%d")

    return {
        "type": "bill_due",
        "provider": "HDFC Bank",
        "amount": amount,
        "currency": "INR",
        "due_date": due_date,
    }

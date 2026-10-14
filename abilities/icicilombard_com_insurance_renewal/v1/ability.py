"""Ability icicilombard_com_insurance_renewal v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'icicilombard.com', 'type': 'insurance_renewal', 'subject_keywords': ['expires', 'insurance', 'policy', 'renew']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date']

import re
from datetime import datetime


def extract(text: str) -> dict:
    if not isinstance(text, str):
        raise ValueError("text must be a string")

    amount_match = re.search(r"Renewal\s+premium\s*:\s*₹\s*([0-9][0-9,]*\.?[0-9]*)", text, re.IGNORECASE)
    if not amount_match:
        raise ValueError("Missing renewal premium label")

    date_match = re.search(r"expires\s+on\s+([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})", text, re.IGNORECASE)
    if not date_match:
        raise ValueError("Missing expiry date label")

    amount_str = amount_match.group(1).replace(",", "")
    amount = float(amount_str)

    raw_date = date_match.group(1).strip()
    parsed_date = None
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            parsed_date = datetime.strptime(raw_date, fmt)
            break
        except ValueError:
            continue
    if parsed_date is None:
        raise ValueError("Invalid expiry date format")

    return {
        "type": "insurance_renewal",
        "provider": "ICICI Lombard",
        "amount": amount,
        "currency": "INR",
        "due_date": parsed_date.strftime("%Y-%m-%d"),
    }

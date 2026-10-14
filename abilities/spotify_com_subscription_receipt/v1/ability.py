"""Ability spotify_com_subscription_receipt v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'spotify.com', 'type': 'subscription_receipt', 'subject_keywords': ['premium', 'receipt', 'spotify']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date', 'service']

import re
from datetime import datetime


def extract(text: str) -> dict:
    amount_match = re.search(r"Spotify\s+Premium\s+Individual\s+[—-]\s*Rs\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*/\s*month", text, re.IGNORECASE)
    if not amount_match:
        raise ValueError("Missing Spotify Premium amount label")

    due_match = re.search(r"Your\s+next\s+payment\s+of\s+Rs\s*[0-9][0-9,]*(?:\.[0-9]+)?\s+is\s+on\s+([0-9]{2}/[0-9]{2}/[0-9]{4})\.", text, re.IGNORECASE)
    if not due_match:
        raise ValueError("Missing next payment due date label")

    amount = float(amount_match.group(1).replace(',', ''))
    due_date = datetime.strptime(due_match.group(1), "%d/%m/%Y").strftime("%Y-%m-%d")

    return {
        "type": "subscription_receipt",
        "provider": "Spotify",
        "amount": amount,
        "currency": "INR",
        "due_date": due_date,
        "service": "Spotify",
    }

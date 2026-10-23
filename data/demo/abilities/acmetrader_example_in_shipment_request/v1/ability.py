"""Ability acmetrader_example_in_shipment_request v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'acmetrader.example.in', 'type': 'shipment_request', 'subject_keywords': ['request', 'shipment']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'amount', 'currency', 'due_date', 'topic', 'category']

import re
from decimal import Decimal


def extract(text: str) -> dict:
    subject_match = re.search(r'(?mi)^Subject:\s*(.+?)\s*$', text)
    if not subject_match:
        raise ValueError('Missing Subject label')

    amount_match = re.search(r'(?mi)^Total\s+Value:\s*Rs\s*([0-9][0-9,]*(?:\.\d+)?)\s*$', text)
    if not amount_match:
        raise ValueError('Missing Total Value label')

    due_date_match = re.search(r'(?mi)^Requested\s+Dispatch\s+Date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*$', text)
    if not due_date_match:
        raise ValueError('Missing Requested Dispatch Date label')

    amount = float(Decimal(amount_match.group(1).replace(',', '')))
    subject = subject_match.group(1).strip()
    topic_match = re.match(r'(Shipment\s+Request)\b', subject, re.I)
    topic = topic_match.group(1).strip() if topic_match else subject
    if not topic:
        raise ValueError('Empty topic')

    return {
        'type': 'other',
        'provider': 'Acme Traders',
        'amount': amount,
        'currency': 'INR',
        'due_date': due_date_match.group(1),
        'topic': topic,
        'category': 'shipment_request',
    }

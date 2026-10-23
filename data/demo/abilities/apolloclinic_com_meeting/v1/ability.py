"""Ability apolloclinic_com_meeting v1: compiled by Sorted from 5 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'apolloclinic.com', 'type': 'meeting', 'subject_keywords': ['anjali', 'appointment', 'confirmed', 'mehta']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'currency', 'due_date', 'event_time', 'person']

import re
from dateutil import parser


def extract(text: str) -> dict:
    if not re.search(r'^From:\s*Apollo Clinic\b', text, re.IGNORECASE | re.MULTILINE):
        raise ValueError('Missing From label')

    if not re.search(r'^Subject:\s*Appointment confirmed:', text, re.IGNORECASE | re.MULTILINE):
        raise ValueError('Missing Subject label')

    person_match = re.search(
        r'Appointment\s+confirmed\s+for\s+(.+?)\s+with\s+Dr\.',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not person_match:
        raise ValueError('Missing appointment person label')
    person = re.sub(r'\s+', ' ', person_match.group(1)).strip()

    body_date_match = re.search(r'^Date:\s*([A-Za-z]+,\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*$', text, re.IGNORECASE | re.MULTILINE)
    if not body_date_match:
        raise ValueError('Missing appointment Date label')
    due_date = parser.parse(body_date_match.group(1).strip(), dayfirst=True).date().isoformat()

    time_match = re.search(r'^Time:\s*(.+?)\s*$', text, re.IGNORECASE | re.MULTILINE)
    if not time_match:
        raise ValueError('Missing Time label')
    event_time = parser.parse(time_match.group(1).strip()).strftime('%H:%M')

    return {
        'type': 'meeting',
        'provider': 'Apollo Clinic',
        'currency': 'INR',
        'due_date': due_date,
        'event_time': event_time,
        'person': person,
    }

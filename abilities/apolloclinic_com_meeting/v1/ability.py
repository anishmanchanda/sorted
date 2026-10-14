"""Ability apolloclinic_com_meeting v1: compiled by Sorted from 3 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'apolloclinic.com', 'type': 'meeting', 'subject_keywords': ['anjali', 'appointment', 'confirmed', 'mehta']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'currency', 'due_date', 'event_time', 'person']

import re
from datetime import datetime


def extract(text: str) -> dict:
    person_match = re.search(
        r'Appointment\s+confirmed\s+for\s+(.+?)\s+with\s+Dr\.',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not person_match:
        raise ValueError('Missing appointment person label')
    person = ' '.join(person_match.group(1).split())

    date_match = re.search(
        r'\bDate:\s*([A-Za-z]+,\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})',
        text,
        re.IGNORECASE,
    )
    if not date_match:
        raise ValueError('Missing Date label')
    try:
        due_date = datetime.strptime(' '.join(date_match.group(1).replace(',', ', ').split()), '%A, %d %B %Y').strftime('%Y-%m-%d')
    except ValueError:
        try:
            due_date = datetime.strptime(' '.join(date_match.group(1).replace(',', ', ').split()), '%A, %d %b %Y').strftime('%Y-%m-%d')
        except ValueError:
            raise ValueError('Invalid appointment date format')

    time_match = re.search(r'\bTime:\s*(\d{1,2}:\d{2}\s*[AP]M)\b', text, re.IGNORECASE)
    if not time_match:
        raise ValueError('Missing Time label')
    try:
        event_time = datetime.strptime(time_match.group(1).upper().replace(' ', ''), '%I:%M%p').strftime('%H:%M')
    except ValueError:
        raise ValueError('Invalid appointment time format')

    return {
        'type': 'meeting',
        'provider': 'Apollo Clinic',
        'currency': 'INR',
        'due_date': due_date,
        'event_time': event_time,
        'person': person,
    }

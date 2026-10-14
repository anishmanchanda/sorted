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
    person = re.sub(r'\s+', ' ', person_match.group(1)).strip()

    date_match = re.search(
        r'(?mi)^Date:\s*([A-Za-z]+,\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*$',
        text,
    )
    if not date_match:
        raise ValueError('Missing appointment Date label')
    date_str = re.sub(r'\s+', ' ', date_match.group(1)).strip()
    try:
        due_date = datetime.strptime(date_str, '%A, %d %B %Y').date().isoformat()
    except ValueError:
        try:
            due_date = datetime.strptime(date_str, '%A, %d %b %Y').date().isoformat()
        except Exception as e:
            raise ValueError('Invalid appointment date') from e

    time_match = re.search(r'(?mi)^Time:\s*([^\n\r]+?)\s*$', text)
    if not time_match:
        raise ValueError('Missing Time label')
    time_str = re.sub(r'\s+', ' ', time_match.group(1)).strip()
    parsed_time = None
    for fmt in ('%I:%M %p', '%I %p', '%H:%M'):
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            break
        except ValueError:
            continue
    if parsed_time is None:
        raise ValueError('Invalid appointment time')
    event_time = parsed_time.strftime('%H:%M')

    return {
        'type': 'meeting',
        'provider': 'Apollo Clinic',
        'currency': 'INR',
        'due_date': due_date,
        'event_time': event_time,
        'person': person,
    }

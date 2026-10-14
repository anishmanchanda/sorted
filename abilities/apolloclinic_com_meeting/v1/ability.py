"""Ability apolloclinic_com_meeting v1: compiled by Sorted from 4 accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {'kind': 'email', 'sender_key': 'apolloclinic.com', 'type': 'meeting', 'subject_keywords': ['anjali', 'appointment', 'confirmed', 'mehta']}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = ['type', 'provider', 'currency', 'due_date', 'event_time', 'person']

import re
from datetime import datetime


def _parse_date(value: str) -> str:
    value = value.strip()
    for fmt in ("%A, %d %B %Y", "%d %B %Y", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    raise ValueError("Could not parse date")



def _parse_time(value: str) -> str:
    value = value.strip()
    for fmt in ("%I:%M %p", "%H:%M", "%H%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            pass
    raise ValueError("Could not parse time")



def extract(text: str) -> dict:
    if not re.search(r"From:\s*Apollo Clinic\b", text, re.IGNORECASE):
        raise ValueError("Missing Apollo Clinic sender")

    person_match = re.search(
        r"Appointment\s+confirmed\s+for\s+(.+?)\s+with\s+Dr\.",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not person_match:
        person_match = re.search(
            r"SUMMARY:.*?\((.+?)\)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
    if not person_match:
        raise ValueError("Missing appointment person")
    person = re.sub(r"\s+", " ", person_match.group(1)).strip()

    date_match = re.search(r"^Date:\s*([A-Za-z]+,\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*$", text, re.MULTILINE)
    if date_match:
        due_date = _parse_date(date_match.group(1))
    else:
        dtstart_match = re.search(r"DTSTART[^:]*:(\d{8})T(\d{4})", text)
        if not dtstart_match:
            raise ValueError("Missing appointment date")
        due_date = _parse_date(dtstart_match.group(1))

    time_match = re.search(r"^Time:\s*([0-9]{1,2}:[0-9]{2}\s*[AP]M)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if time_match:
        event_time = _parse_time(re.sub(r"\s+", " ", time_match.group(1)).upper())
    else:
        dtstart_match = re.search(r"DTSTART[^:]*:\d{8}T(\d{4})", text)
        if not dtstart_match:
            raise ValueError("Missing appointment time")
        event_time = _parse_time(dtstart_match.group(1))

    return {
        "type": "meeting",
        "provider": "Apollo Clinic",
        "currency": "INR",
        "due_date": due_date,
        "event_time": event_time,
        "person": person,
    }

"""The typed output of every extractor (LLM or compiled) and the rules it must pass."""

import re
from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

EmailType = Literal[
    "bill_due", "premium_due", "insurance_renewal", "subscription_receipt",
    "subscription_price_change", "meeting", "meeting_request", "document_expiry", "other", "ignore",
]
TYPES: tuple[str, ...] = EmailType.__args__
NEEDS_AMOUNT = {"bill_due", "premium_due", "insurance_renewal", "subscription_receipt", "subscription_price_change"}


class Extraction(BaseModel):
    type: EmailType
    provider: str | None = None
    amount: float | None = None  # bill total / premium / charged price / new price
    currency: str = "INR"
    due_date: date | None = None  # due / expiry / next billing / effective date / appointment date
    service: str | None = None  # subscriptions
    old_price: float | None = None
    new_price: float | None = None
    event_time: str | None = None  # HH:MM for meetings
    person: str | None = None
    topic: str | None = None  # meeting requests: what it is about
    document_type: str | None = None
    category: str | None = None  # other: a snake_case label for a new kind of message, e.g. "shipment_request"


def validate(ext: Extraction, received_at: datetime) -> list[str]:
    """Problems with an extraction; empty list means it passes."""
    if ext.type == "ignore":
        return []
    problems = []
    if not (ext.provider or "").strip():
        problems.append("provider is empty")
    if ext.type in NEEDS_AMOUNT and not (ext.amount and ext.amount > 0):
        problems.append("amount must be > 0")
    if ext.type == "subscription_price_change" and not (ext.new_price and ext.new_price > 0):
        problems.append("new_price must be > 0")
    if ext.type == "other" and not re.fullmatch(r"[a-z][a-z0-9_]{2,39}", ext.category or ""):
        problems.append("category must be a snake_case label")
    if ext.due_date is None:
        if ext.type != "other":  # a new kind of message may have no date
            problems.append("due_date missing")
    else:
        start, end = received_at.date() - timedelta(days=45), received_at.date() + timedelta(days=400)
        if not start <= ext.due_date <= end:
            problems.append(f"due_date {ext.due_date} outside {start}..{end}")
    return problems

"""Turn a validated extraction into state rows. Duplicates are linked, conflicts are flagged, never overwritten."""

import re
from datetime import timedelta

from sqlalchemy import select

from brain import db
from brain.validate import Extraction

OBLIGATION_TYPE = {
    "bill_due": "bill", "premium_due": "premium", "insurance_renewal": "renewal",
    "subscription_receipt": "subscription", "meeting": "meeting",
}
_STOP = {"bank", "ltd", "limited", "india", "of", "the", "co", "company", "insurance", "power", "govt"}


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def provider_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return a == b
    ta, tb = _tokens(a), _tokens(b)
    sa, sb = " ".join(sorted(ta)), " ".join(sorted(tb))
    return sa in sb or sb in sa or bool((ta & tb) - _STOP)


def apply(s, src: db.SourceRecord, ext: Extraction, problems: list[str]) -> str:
    """Write facts for one extraction. Returns a short outcome label for logs."""
    if ext.type == "ignore":
        return "ignored"
    if ext.type == "subscription_price_change":
        return "price_change"  # acted on by the rules engine, which owns subscription price updates
    if ext.type == "document_expiry":
        s.add(db.Document(type=ext.document_type or "document", expiry=ext.due_date, source_id=src.id))
        return "document"
    if ext.type == "subscription_receipt" and not problems:
        service = ext.service or ext.provider
        sub = s.scalar(select(db.Subscription).where(db.Subscription.service == service))
        if sub is None:
            s.add(db.Subscription(service=service, price=ext.amount, source_id=src.id))
        else:  # a receipt is what was actually charged: that is the current price
            sub.price, sub.source_id = ext.amount, src.id

    ob = db.Obligation(
        type=OBLIGATION_TYPE[ext.type], provider=ext.provider or "?", amount=ext.amount, currency=ext.currency,
        due_date=ext.due_date, repeat_rule="monthly" if ext.type in ("bill_due", "premium_due",
                                                                     "subscription_receipt") else "",
        status="flagged" if problems else "open", confidence=0.4 if problems else 1.0,
        note="; ".join(problems), source_id=src.id,
    )
    if ext.due_date:
        near = s.scalars(select(db.Obligation).where(
            db.Obligation.type == ob.type,
            db.Obligation.due_date.between(ext.due_date - timedelta(days=7), ext.due_date + timedelta(days=7)),
        )).all()
        for old in (o for o in near if provider_match(o.provider, ob.provider)):
            same_amount = (old.amount is None and ob.amount is None) or (
                old.amount is not None and ob.amount is not None and abs(float(old.amount) - ob.amount) < 0.01)
            if same_amount and old.due_date == ob.due_date:
                db.audit(s, "state", "duplicate", obligation=old.id, source=src.id)
                return "duplicate"
            ob.status, old.status = "flagged", "flagged"
            ob.confidence = min(ob.confidence, 0.5)
            ob.note = "; ".join(filter(None, [ob.note, f"conflicts with obligation #{old.id}"]))
            old.note = "; ".join(filter(None, [old.note, f"conflicting fact from source #{src.id}"]))
            db.audit(s, "state", "conflict", obligation=old.id, source=src.id)
    s.add(ob)
    return ob.status

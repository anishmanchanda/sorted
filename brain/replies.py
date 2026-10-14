"""Rule-based reply handlers, no LLM: `1` / `done` logs a dose, `snooze 1h`, `paid [provider]`.
Anything else returns None and goes to the orchestrator."""

import re
import uuid
from datetime import timedelta

from sqlalchemy import select

from brain import db, rules, scheduler
from brain.state import provider_match

_DONE = re.compile(r"^\s*(1|done|taken)\s*[.!]?\s*$", re.I)
_SNOOZE = re.compile(r"^\s*snooze\s+(\d+)\s*(m|min|mins|minutes?|h|hr|hrs|hours?)\s*$", re.I)
_PAID = re.compile(r"^\s*paid(?:\s+(.+?))?\s*[.!]?\s*$", re.I)


def _last_reminder(s, field: str | None = None) -> dict | None:
    for entry in s.scalars(select(db.AuditLog).where(db.AuditLog.action == "reminded")
                           .order_by(db.AuditLog.id.desc()).limit(50)):
        if field is None or entry.detail.get(field):
            return entry.detail
    return None


def _log_dose(s) -> str:
    last = _last_reminder(s, "medication_id")
    med = s.get(db.Medication, last["medication_id"]) if last else None
    if med is None:
        return "No medicine reminder to log against yet."
    med.stock = max(0, med.stock - 1)
    s.add(db.DoseLog(medication_id=med.id))
    db.audit(s, "reply", "dose_logged", medication=med.id, stock=med.stock)
    ctx = {"name": med.name, "stock": med.stock, "person": med.person,
           "whose": "your" if med.person in ("me", "") else f"{med.person}'s"}
    _, effects = rules.run(s, None, "medication_stock", ctx)
    s.commit()
    for effect in effects:
        effect()
    return f"Logged {ctx['whose']} {med.name}. {med.stock} left."


def _snooze(s, amount: int, unit: str) -> str:
    last = _last_reminder(s)
    if last is None:
        return "Nothing to snooze."
    delta = timedelta(minutes=amount) if unit.lower().startswith("m") else timedelta(hours=amount)
    run_at = scheduler.now() + delta
    scheduler.create_reminder(last["text"], run_at, key=f"snooze:{uuid.uuid4().hex[:8]}",
                              obligation_id=last.get("obligation_id"), medication_id=last.get("medication_id"))
    db.audit(s, "reply", "snoozed", until=f"{run_at:%Y-%m-%d %H:%M}")
    s.commit()
    return f"Snoozed until {run_at:%H:%M}."


def _paid(s, provider: str | None) -> str:
    if provider:
        open_obs = s.scalars(select(db.Obligation).where(db.Obligation.status.in_(("open", "flagged")))
                             .order_by(db.Obligation.due_date)).all()
        ob = next((o for o in open_obs if provider_match(o.provider, provider)), None)
    else:
        last = _last_reminder(s, "obligation_id")
        ob = s.get(db.Obligation, last["obligation_id"]) if last else None
    if ob is None:
        return "I couldn't tell which bill you paid. Try 'paid HDFC'."
    ob.status = "paid"
    db.audit(s, "reply", "mark_paid", obligation=ob.id)
    s.commit()
    amount = f" ₹{float(ob.amount):,.2f}" if ob.amount else ""
    return f"Marked {ob.provider}{amount} (due {ob.due_date:%d %b}) as paid."


def handle(text: str) -> str | None:
    with db.Session() as s:
        if _DONE.match(text):
            return _log_dose(s)
        if m := _SNOOZE.match(text):
            return _snooze(s, int(m.group(1)), m.group(2))
        if m := _PAID.match(text):
            return _paid(s, m.group(1))
    return None

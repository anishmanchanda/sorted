"""Rules as data: the YAML files in this folder, run with no LLM.

A rule has a `when` (extraction type + an optional `<name> <op> <name|number>` condition) and a list of
actions from a fixed set. Side effects (reminders, chat alerts) are returned as callables and run after the
state transaction commits. Each action needs its permission to be listed in the rule.
"""

import operator
import re
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml
from sqlalchemy import select

from brain import db, notify, scheduler
from brain.state import provider_match
from brain.validate import Extraction

RULES_DIR = Path(__file__).parent
_COND = re.compile(r"^\s*(\w+)\s*(>=|<=|==|!=|>|<)\s*([\w.]+)\s*$")
_OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq,
        "!=": operator.ne}
PERMISSION = {"update_subscription": "state.write", "reminder": "reminder.create", "send_message": "chat.send_self"}


def load_rules() -> list[dict]:
    return [yaml.safe_load(p.read_text()) for p in sorted(RULES_DIR.glob("*.yaml"))]


def _subscription(s, service: str) -> db.Subscription | None:
    return next((x for x in s.scalars(select(db.Subscription)) if provider_match(x.service, service)), None)


def context(s, ext: Extraction) -> dict:
    ctx = ext.model_dump(exclude_none=True)
    ctx["service"] = ext.provider or ext.service  # brand, not plan name
    ctx["effective_date"] = ext.due_date
    sub = _subscription(s, ctx["service"]) if ctx["service"] else None
    ctx["stored_price"] = float(sub.price) if sub else ext.old_price
    return ctx


def holds(condition: str, ctx: dict) -> bool:
    m = _COND.match(condition)
    if not m:
        raise ValueError(f"unsupported condition: {condition!r}")
    left, op, right = m.groups()
    a = ctx.get(left)
    b = ctx.get(right) if not re.fullmatch(r"-?\d+(\.\d+)?", right) else float(right)
    return a is not None and b is not None and _OPS[op](a, b)


def fmt(template: str, ctx: dict) -> str:
    def show(v):
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        if isinstance(v, date):
            return f"{v:%d %b %Y}"
        return v

    return template.format(**{k: show(v) for k, v in ctx.items()})


def _update_subscription(s, src, ctx, spec) -> None:
    sub = _subscription(s, ctx["service"])
    if sub is None:
        s.add(db.Subscription(service=ctx["service"], price=ctx["new_price"], effective_date=ctx["effective_date"],
                              source_id=src.id))
    else:
        sub.price, sub.effective_date, sub.source_id = ctx["new_price"], ctx["effective_date"], src.id


def _reminder(s, src, ctx, spec) -> Callable[[], None]:
    day = ctx[spec.get("date_field", "effective_date")] - timedelta(days=int(spec.get("days_before", 0)))
    run_at = datetime.combine(day, time.fromisoformat(spec.get("at", "09:00")))
    text, key = fmt(spec["text"], ctx), f"rule:{ctx['service']}:{ctx['effective_date']}:{spec.get('days_before', 0)}"
    return lambda: scheduler.create_reminder(text, run_at, key=key)


def _send_message(s, src, ctx, spec) -> Callable[[], None]:
    text = fmt(spec["template"], ctx)
    return lambda: notify.send_self(text)


ACTIONS = {"update_subscription": _update_subscription, "reminder": _reminder, "send_message": _send_message}


def apply(s, src: db.SourceRecord, ext: Extraction) -> tuple[list[str], list[Callable[[], None]]]:
    """Run every matching rule. Returns (fired rule names, side effects to run after commit)."""
    fired, after_commit = [], []
    ctx = context(s, ext)  # state as it was before any rule ran
    for rule in load_rules():
        when = rule["when"]
        if when.get("type") != ext.type:
            continue
        if "condition" in when and not holds(when["condition"], ctx):
            continue
        for action in rule["then"]:
            ((name, spec),) = action.items()
            if name not in ACTIONS or PERMISSION[name] not in rule.get("permissions", []):
                db.audit(s, "rule", "action_denied", rule=rule["rule"], action=name)
                continue
            effect = ACTIONS[name](s, src, ctx, spec or {})
            if effect:
                after_commit.append(effect)
        db.audit(s, "rule", rule["rule"], source=src.id, service=ctx.get("service"), new_price=ctx.get("new_price"))
        fired.append(rule["rule"])
    return fired, after_commit

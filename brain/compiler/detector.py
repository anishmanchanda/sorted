"""Pattern detector: group accepted LLM extract traces by (source kind, sender, email type).
A group with >= BRAIN_COMPILE_AFTER traces becomes a `candidate`; a degraded ability with new traces
since it broke becomes a `candidate` for version n+1 (repair)."""

import re
from collections import defaultdict

from sqlalchemy import select

from brain import config, db, skills
from brain.messages import sender_key
from brain.validate import TYPES

_STOP = {"your", "from", "with", "this", "that", "have", "ready", "here", "about"}
_MONTHS = {"january", "february", "march", "april", "june", "july", "august", "september", "october", "november",
           "december", "sept"}


def subject_words(subject: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", subject.lower()) if len(w) >= 4 and w not in _STOP | _MONTHS
            and set(w) != {"x"}}  # skip redaction masks


def ability_name(key: tuple[str, str, str]) -> str:
    kind, skey, etype = key
    return f"{'sms_' if kind == 'sms' else ''}{re.sub(r'[^a-z0-9]+', '_', skey.lower()).strip('_')}_{etype}"


def groups(s) -> dict[tuple[str, str, str], list[tuple[db.Trace, db.SourceRecord]]]:
    rows = s.execute(
        select(db.Trace, db.SourceRecord).join(db.SourceRecord, db.Trace.input_ref == db.SourceRecord.id)
        .where(db.Trace.task_kind == "extract", db.Trace.handler == "llm", db.Trace.accepted.is_(True))
        .order_by(db.Trace.id)
    ).all()
    out = defaultdict(list)
    for trace, src in rows:
        etype = trace.output_json.get("type")
        if etype == "other":  # a new kind of message: its category is the type a parser is compiled for
            etype = trace.output_json.get("category")
        if etype and etype != "ignore":  # ignore-mail is the local classifier's job (brain.ml), not a parser's
            out[(src.kind, sender_key(src.kind, src.sender), etype)].append((trace, src))
    return out


def make_trigger(key, items) -> dict:
    kind, skey, etype = key
    words = set.intersection(*(subject_words(src.subject) for _, src in items)) if kind == "email" else set()
    return {"kind": kind, "sender_key": skey, "type": etype, "subject_keywords": sorted(words)[:6]}


def items_for(s, ability: db.Ability) -> list[tuple[db.Trace, db.SourceRecord]]:
    t = ability.trigger_json
    return groups(s).get((t["kind"], t["sender_key"], t["type"]), [])


def scan(s) -> list[db.Ability]:
    """Create candidates where patterns repeat. Returns abilities that need (re)compiling."""
    compile_after = int(config.env("BRAIN_COMPILE_AFTER", "3"))
    todo = []
    for key, items in groups(s).items():
        if key[2] not in TYPES and not skills.is_active(s, key[2]):  # a new category: only once the user agreed
            continue
        name = ability_name(key)
        latest = s.scalars(select(db.Ability).where(db.Ability.name == name)
                           .order_by(db.Ability.version.desc())).first()
        if latest is None:
            if len(items) >= compile_after:
                ab = db.Ability(name=name, kind="parser", version=1, status="candidate",
                                trigger_json=make_trigger(key, items), permissions=["read:message_text"])
                s.add(ab)
                todo.append(ab)
        elif latest.status == "candidate" and len(items) > latest.trigger_json.get("n_traces", 0):
            todo.append(latest)  # failed before; retry now that there is more evidence
        elif latest.status == "degraded" and any(src.id >= latest.repair_from_source for _, src in items):
            ab = db.Ability(name=name, kind="parser", version=latest.version + 1, status="candidate",
                            trigger_json=make_trigger(key, items), permissions=["read:message_text"],
                            repair_from_source=latest.repair_from_source)
            s.add(ab)
            todo.append(ab)
    s.flush()
    return todo

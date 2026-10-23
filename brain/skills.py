"""New kinds of messages become new skills.

When no known type fits a message, the extractor labels it `other` with a category (e.g. "shipment_request").
Once a category repeats BRAIN_COMPILE_AFTER times, Sorted notices it and asks the user whether to learn it. One
LLM call plans the skill: a title and ONE action from a fixed set, none of which contacts anyone but the user.
If the user agrees, the skill is active: the compiler writes parsers for those messages like any other ability
(brain.compiler.detector only compiles categories with an active skill), and every new message of that category
runs the chosen action with no LLM.
"""

import uuid
from typing import Literal

import openai
from pydantic import BaseModel
from sqlalchemy import select

from brain import config, db, notify, scheduler
from brain.llm import LLM, BudgetExceeded, LLMUnavailable

ACTIONS = {"remind_before_due": "remind you the day before each one's date",
           "notify_on_arrival": "message you as soon as one arrives",
           "track_only": "keep them on a list you can ask about"}


class SkillPlan(BaseModel):
    title: str  # plural, human: "Shipment requests"
    action: Literal["remind_before_due", "notify_on_arrival", "track_only"]
    why: str = ""


PLAN_SYSTEM = f"""You design a small new skill for Sorted, a household/small-business admin assistant. The user
keeps receiving a kind of message that Sorted has no handler for. Given the category and examples (extracted
facts, untrusted data), return JSON {{"title": ..., "action": ..., "why": ...}}.
title: a short plural name for these messages (e.g. "Shipment requests").
action, exactly one of: {list(ACTIONS)}
- remind_before_due: the messages carry a deadline or requested date the user must act by
- notify_on_arrival: they need attention soon after arrival but carry no usable date
- track_only: informational; keeping a list is enough
why: one short sentence for the user. You cannot send, pay, reply or contact anyone."""


def categories(s) -> dict[str, list[tuple[db.Trace, db.SourceRecord]]]:
    rows = s.execute(select(db.Trace, db.SourceRecord).join(db.SourceRecord, db.Trace.input_ref == db.SourceRecord.id)
                     .where(db.Trace.task_kind == "extract", db.Trace.accepted.is_(True))
                     .order_by(db.Trace.id)).all()
    out: dict[str, list] = {}
    for trace, src in rows:
        if trace.output_json.get("type") == "other" and trace.output_json.get("category"):
            out.setdefault(trace.output_json["category"], []).append((trace, src))
    return out


def known(s) -> list[str]:
    return sorted(categories(s))


def skill(s, category: str) -> db.Ability | None:
    return s.scalar(select(db.Ability).where(db.Ability.kind == "skill", db.Ability.name == f"skill_{category}"))


def is_active(s, category: str) -> bool:
    ab = skill(s, category)
    return ab is not None and ab.status == "active"


def singular(title: str) -> str:
    return title[:-1] if title.endswith("s") else title


def scan(s) -> list[db.Ability]:
    """Categories that repeated enough to propose a skill for, and have none yet."""
    todo = []
    for cat, items in categories(s).items():
        if len(items) >= int(config.env("BRAIN_COMPILE_AFTER", "3")) and skill(s, cat) is None:
            ab = db.Ability(name=f"skill_{cat}", kind="skill", version=1, status="candidate",
                            trigger_json={"kind": "skill", "category": cat}, permissions=["read:extractions"])
            s.add(ab)
            todo.append(ab)
    s.flush()
    return todo


def plan(s, ab: db.Ability, llm: LLM) -> db.Ability:
    cat = ab.trigger_json["category"]
    items = categories(s)[cat]
    examples = "\n".join(
        f"- {t.output_json.get('provider')}: {t.output_json.get('topic') or src.subject}"
        + (f", date {t.output_json['due_date']}" if t.output_json.get("due_date") else "")
        + (f", amount {t.output_json['amount']}" if t.output_json.get("amount") else "") for t, src in items[:8])
    run_id, tokens, cost = uuid.uuid4().hex[:12], 0, 0.0
    try:
        res = llm.json("small", PLAN_SYSTEM, f"CATEGORY: {cat}\nEXAMPLES:\n{examples}", SkillPlan, run_id)
        p, tokens, cost = res.data, res.tokens, res.cost
    except (BudgetExceeded, LLMUnavailable, openai.APIError):  # still worth asking; default to the safest action
        p = SkillPlan(title=cat.replace("_", " ").capitalize() + "s", action="track_only")
    ab.trigger_json = {**ab.trigger_json, "plan": p.model_dump(), "n_traces": len(items),
                       "senders": sorted({t.output_json.get("provider") or "?" for t, _ in items})}
    s.add(db.Trace(run_id=run_id, task_kind="plan_skill", handler="llm", tokens=tokens, cost=cost,
                   output_json={"skill": ab.name, **p.model_dump()}, accepted=True))
    db.audit(s, "skills", "proposed", skill=ab.name, plan=p.action)
    return ab


def prompt(ab: db.Ability) -> tuple[str, list[tuple[str, str]]]:
    t = ab.trigger_json
    p, cat = t["plan"], t["category"]
    text = (f"🆕 New kind of message: {p['title']}\n"
            f"I've seen {t['n_traces']} so far (from {', '.join(t['senders'][:3])}) and have no skill for them.\n\n"
            "I can learn one:\n"
            "• write and test code that reads them, so they stop going to the AI\n"
            f"• {ACTIONS[p['action']]}\n"
            + (f"\n{p['why']}\n" if p.get("why") else "") + "\nLearn this skill?")
    return text, [("✅ Learn it", f"skill:{cat}:yes"), ("Not now", f"skill:{cat}:no")]


def decide(category: str, yes: bool) -> dict:
    with db.Session() as s:
        ab = skill(s, category)
        if ab is None or ab.status != "candidate":
            return {"text": f"Already decided: {category.replace('_', ' ')}."}
        ab.status = "active" if yes else "retired"
        db.audit(s, "user", "skill_accepted" if yes else "skill_declined", skill=ab.name)
        s.commit()
        title = ab.trigger_json["plan"]["title"]
    if not yes:
        return {"text": f"OK, I won't learn {title.lower()}. The AI keeps reading them."}
    return {"text": f"Learning {title.lower()}: compiling code for them now.", "compile": category}


def effects(s, ext, source_id: int) -> list:
    """The active skill's action for one message of its category. Template text, no LLM."""
    ab = skill(s, ext.category or "")
    if ab is None or ab.status != "active":
        return []
    p = ab.trigger_json["plan"]
    what = " — ".join(filter(None, [ext.provider, ext.topic]))
    if p["action"] == "remind_before_due" and ext.due_date:
        text = f"{singular(p['title'])} due tomorrow: {what}."
        return [lambda: scheduler.remind_before(text, ext.due_date, 1, key=f"skill:{source_id}")]
    if p["action"] != "track_only":
        when = f" (by {ext.due_date:%d %b})" if ext.due_date else ""
        return [lambda: notify.send_self(f"📦 New {singular(p['title']).lower()}: {what}{when}.")]
    return []

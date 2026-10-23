"""Button presses from Telegram or the web dashboard. Action ids: approve:<ability>, reject:<ability>,
meet:<source_id>:yes|no|other|at:<iso time>, mail:<source_id>:send|skip, skill:<category>:yes|no.
The user is the only one who can trigger these."""

from datetime import datetime

from sqlalchemy import select

from brain import db, meetings, skills
from brain.compiler import registry


def describe(ab: db.Ability) -> str:
    t = ab.trigger_json
    if ab.kind == "skill":
        p = t.get("plan", {})
        return f"handle {p.get('title', t.get('category', '')).lower()}: {skills.ACTIONS.get(p.get('action'), '')}"
    if ab.kind == "query":
        return f"answer '{t.get('intent', '').replace('_', ' ')}' questions without the LLM"
    return f"read {t.get('sender_key')} {t.get('type', '').replace('_', ' ')} messages without the LLM"


def approval_prompt(result: dict) -> tuple[str, list[tuple[str, str]]]:
    with db.Session() as s:
        ab = s.scalars(select(db.Ability).where(db.Ability.name == result["ability"],
                                                db.Ability.version == result["version"])).first()
        what = describe(ab)
    text = (f"🧪 New ability {result['ability']} v{result['version']} passed its tests ({result['visible']} shown + "
            f"{result['held_out']} held-out cases, held-out pass {100 * result['held_out_pass_rate']:.0f}%). "
            f"It would {what}. Approve it for shadow mode?")
    return text, [("✅ Approve", f"approve:{result['ability']}"), ("❌ Reject", f"reject:{result['ability']}")]


def handle(action: str) -> dict:
    """Returns {text} plus, depending on the action: {ics, title, link, meet} (meeting booked), followup (a next
    question with buttons), awaiting_time (the next chat message is a time), compile (a skill to compile now)."""
    kind, _, rest = action.partition(":")
    if kind == "meet":
        source_id, _, answer = rest.partition(":")
        if answer == "other":
            return {"text": "When suits you? Reply with a time, e.g. \"Friday 5pm\" or \"14 Jun 11:30\".",
                    "awaiting_time": int(source_id)}
        if answer.startswith("at:"):
            return meetings.decide(int(source_id), True, datetime.fromisoformat(answer[3:]))
        return meetings.decide(int(source_id), answer == "yes")
    if kind == "mail":
        source_id, _, answer = rest.partition(":")
        return meetings.send(int(source_id), answer == "send")
    if kind == "skill":
        category, _, answer = rest.rpartition(":")
        return skills.decide(category, answer == "yes")
    with db.Session() as s:
        if kind == "approve":
            ab = registry.approve(s, rest, actor="user")
            s.commit()
            return {"text": f"Approved {ab.name} v{ab.version}: it now runs in shadow mode next to the LLM."
                    if ab else f"Nothing to approve for {rest}."}
        if kind == "reject":
            ab = s.scalars(select(db.Ability).where(db.Ability.name == rest, db.Ability.status == "tested")
                           .order_by(db.Ability.version.desc())).first()
            if ab:
                ab.status = "retired"
                db.audit(s, "user", "rejected", ability=ab.name, version=ab.version)
                s.commit()
            return {"text": f"Rejected {rest}; the LLM keeps handling it." if ab else f"Nothing to reject for {rest}."}
    return {"text": f"Unknown action {action!r}."}

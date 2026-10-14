"""Ability lifecycle at runtime: match a source to an ability, execute it (sandboxed), shadow-compare it
against the LLM, activate it, degrade it on failure, approve it (human gate tested -> shadow)."""

from pydantic import ValidationError
from sqlalchemy import select

from brain import config, db
from brain.compiler import sandbox
from brain.compiler.detector import subject_words
from brain.compiler.generator import compare
from brain.messages import sender_key
from brain.validate import Extraction, validate

CORE_FIELDS = ("type", "provider", "amount", "due_date")


def matches(trigger: dict, src: db.SourceRecord) -> bool:
    return (trigger.get("kind") == src.kind and trigger.get("sender_key") == sender_key(src.kind, src.sender)
            and set(trigger.get("subject_keywords", [])) <= subject_words(src.subject))


def match(s, src: db.SourceRecord) -> db.Ability | None:
    live = s.scalars(select(db.Ability).where(db.Ability.status.in_(("active", "shadow")))
                     .order_by(db.Ability.version.desc())).all()
    return next((ab for ab in live if matches(ab.trigger_json, src)), None)


def handler(ab: db.Ability) -> str:
    return f"ability:{ab.name}@v{ab.version}"


def execute(ab: db.Ability, src: db.SourceRecord) -> tuple[Extraction | None, str]:
    """Run the ability on one source. Returns (validated extraction, "") or (None, reason)."""
    r = sandbox.run(ab.code, [src.text], timeout=10)[0]
    ab.runs += 1
    if not r["ok"]:
        err = r["error"]
    elif not r["value"]:
        err = "trigger matched but extraction is empty"
    else:
        try:
            ext = Extraction.model_validate(r["value"])
        except ValidationError as e:
            err = f"output schema: {e.errors()[0]['loc']} {e.errors()[0]['msg']}"
        else:
            problems = validate(ext, src.received_at)
            if not problems:
                return ext, ""
            err = "validation: " + "; ".join(problems)
    ab.failures += 1
    ab.last_error = err
    return None, err


def degrade(s, ab: db.Ability, reason: str, src: db.SourceRecord) -> None:
    ab.status, ab.last_error, ab.repair_from_source = "degraded", reason[:2000], src.id
    db.audit(s, "registry", "degraded", ability=ab.name, version=ab.version, reason=reason[:300], source=src.id)


def activate(s, ab: db.Ability) -> None:
    ab.status = "active"
    for old in s.scalars(select(db.Ability).where(db.Ability.name == ab.name, db.Ability.version < ab.version,
                                                  db.Ability.status != "retired")):
        old.status = "retired"
    db.audit(s, "registry", "activated", ability=ab.name, version=ab.version)


def shadow(s, ab: db.Ability, src: db.SourceRecord, llm_ext: Extraction) -> str:
    """Run the ability next to the LLM. The LLM result is the one used."""
    r = sandbox.run(ab.code, [src.text], timeout=10)[0]
    ab.runs += 1
    if r["ok"] and isinstance(r["value"], dict):  # core fields + whatever the ability outputs (LLMs add extras)
        expected = {k: v for k, v in llm_ext.model_dump(mode="json", exclude_none=True).items()
                    if k in CORE_FIELDS or k in r["value"]}
        bad = compare(expected, r["value"])
    else:
        bad = [r.get("error", "no output")]
    if bad:
        ab.failures += 1
        degrade(s, ab, f"shadow mismatch on {bad}", src)
        return "shadow mismatch -> degraded"
    ab.shadow_matches += 1
    need = int(config.env("BRAIN_SHADOW_RUNS", "2"))
    if ab.shadow_matches >= need:
        activate(s, ab)
        return f"shadow match {ab.shadow_matches}/{need} -> active"
    return f"shadow match {ab.shadow_matches}/{need}"


def approve(s, name: str, actor: str = "user") -> db.Ability | None:
    ab = s.scalars(select(db.Ability).where(db.Ability.name == name, db.Ability.status == "tested")
                   .order_by(db.Ability.version.desc())).first()
    if ab:
        ab.status, ab.shadow_matches = "shadow", 0
        db.audit(s, actor, "approved", ability=ab.name, version=ab.version)
    return ab


def listing(s) -> list[db.Ability]:
    return s.scalars(select(db.Ability).order_by(db.Ability.name, db.Ability.version)).all()

"""Orchestrator: filter -> store source -> ability registry -> agent -> validate -> state -> rules -> trace."""

import uuid

import openai
from sqlalchemy import select

from brain import db, planner, rules, state
from brain.agents import ChatAgent, DocumentAgent, InboxAgent
from brain.compiler import registry
from brain.filters import is_otp, looks_like_injection
from brain.llm import LLM, BudgetExceeded, LLMUnavailable
from brain.messages import Message
from brain.redact import redact
from brain.validate import Extraction, validate


class Orchestrator:
    TOOLS = ("registry.lookup", "agent.inbox", "agent.document", "agent.chat")

    def __init__(self, llm: LLM | None = None):
        self.llm = llm or LLM()
        self.inbox, self.document, self.chat = InboxAgent(self.llm), DocumentAgent(self.llm), ChatAgent(self.llm)

    def ingest(self, msg: Message) -> dict:
        if is_otp(f"{msg.subject}\n{msg.body}"):  # dropped before storage; only the fact of dropping is logged
            with db.Session() as s:
                db.audit(s, "orchestrator", "dropped_otp", kind=msg.kind, sender=msg.sender)
                s.commit()
            return {"outcome": "dropped_otp"}
        with db.Session() as s:
            if s.scalar(select(db.SourceRecord.id).where(db.SourceRecord.body_hash == msg.body_hash)):
                return {"outcome": "already_seen"}
            src = db.SourceRecord(kind=msg.kind, sender=msg.sender, subject=redact(msg.subject),
                                  body_hash=msg.body_hash, received_at=msg.received_at, raw_path=msg.raw_path,
                                  text=msg.redacted_text())
            s.add(src)
            s.flush()
            out = self.process(s, src)
            s.commit()
        for effect in out.pop("after_commit", []):
            effect()
        return out

    def _extract(self, s, src: db.SourceRecord, run_id: str) -> tuple[Extraction, str, int, float, str]:
        """(extraction, handler, tokens, cost, ability event). Registry first, LLM only if needed."""
        if looks_like_injection(src.text):
            db.audit(s, "orchestrator", "suspicious_input", source=src.id)
            return Extraction(type="ignore"), "rule:injection_guard", 0, 0.0, ""
        ability = registry.match(s, src)
        event = ""
        if ability is not None and ability.status == "active":
            ext, err = registry.execute(ability, src)
            if ext is not None:
                return ext, registry.handler(ability), 0, 0.0, "local code"
            registry.degrade(s, ability, err, src)
            event = f"{registry.handler(ability)} failed ({err[:80]}) -> degraded, LLM fallback"
        if ability is None:
            local, event = self._classify(src)
            if local:
                return local
        agent = self.inbox if src.kind == "email" else self.document
        res = agent.extract(src.text, run_id)
        if ability is not None and ability.status == "shadow":
            event = f"{registry.handler(ability)} {registry.shadow(s, ability, src, res.data)}"
        return res.data, "llm", res.tokens, res.cost, event

    @staticmethod
    def _classify(src: db.SourceRecord):
        """Local ML: a confident `ignore` (promotion, newsletter) never reaches the LLM."""
        from brain.ml import classifier

        clf = classifier.current()
        if clf is None:
            return None, ""
        label, conf, layer = clf.predict(src.kind, src.sender, src.subject, src.text)
        if label == "ignore" and conf >= classifier.threshold():
            return (Extraction(type="ignore"), f"ml:{layer}", 0, 0.0,
                    f"local classifier: ignore ({conf:.2f}, {layer})"), ""
        note = f"local classifier unsure ({label} {conf:.2f} < {classifier.threshold()}) -> LLM" if label else ""
        return None, note if label == "ignore" else ""

    def process(self, s, src: db.SourceRecord) -> dict:
        run_id = uuid.uuid4().hex[:12]
        try:
            ext, handler, tokens, cost, event = self._extract(s, src, run_id)
        except (BudgetExceeded, LLMUnavailable, openai.APIError) as e:
            src.status = "queued"
            db.audit(s, "orchestrator", "queued", source=src.id, reason=str(e)[:200])
            return {"outcome": "queued", "source": src.id, "reason": str(e)[:200]}

        problems = validate(ext, src.received_at)
        outcome = state.apply(s, src, ext, problems)
        fired, after_commit = rules.apply(s, src, ext) if not problems else ([], [])
        if outcome == "open":  # relative reminders ("3 days before due"), no LLM
            after_commit.append(lambda: planner.plan_obligations(src.id))
        s.add(db.Trace(run_id=run_id, task_kind="extract", input_ref=src.id, handler=handler, tokens=tokens,
                       cost=cost, output_json=ext.model_dump(mode="json", exclude_none=True), accepted=not problems))
        src.status = "done"
        return {"outcome": outcome, "source": src.id, "handler": handler, "type": ext.type, "problems": problems,
                "extraction": ext, "event": event, "rules": fired, "after_commit": after_commit}

    def drain(self) -> list[dict]:
        """Retry sources that were queued (budget exhausted, provider down)."""
        with db.Session() as s:
            results = [self.process(s, src) for src in
                       s.scalars(select(db.SourceRecord).where(db.SourceRecord.status == "queued")).all()]
            s.commit()
        for out in results:
            for effect in out.pop("after_commit", []):
                effect()
        return results

    def ask(self, question: str) -> str:
        run_id = uuid.uuid4().hex[:12]
        try:
            res = self.chat.answer(question, run_id)
        except (BudgetExceeded, LLMUnavailable, openai.APIError) as e:
            return f"I can't answer right now ({e}). Try /due for a no-AI summary."
        with db.Session() as s:
            s.add(db.Trace(run_id=run_id, task_kind="chat", handler="llm", tokens=res.tokens, cost=res.cost,
                           output_json=res.data.model_dump(), accepted=True))
            s.commit()
        return res.data.answer

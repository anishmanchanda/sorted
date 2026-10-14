"""Orchestrator: filter -> store source -> (ability registry) -> agent -> validate -> state -> trace."""

import uuid

import openai
from sqlalchemy import select

from brain import db, state
from brain.agents import ChatAgent, DocumentAgent, InboxAgent
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
            return out

    def process(self, s, src: db.SourceRecord) -> dict:
        run_id = uuid.uuid4().hex[:12]
        try:
            if looks_like_injection(src.text):
                ext, handler, tokens, cost = Extraction(type="ignore"), "rule:injection_guard", 0, 0.0
                db.audit(s, "orchestrator", "suspicious_input", source=src.id)
            else:
                agent = self.inbox if src.kind == "email" else self.document
                res = agent.extract(src.text, run_id)
                ext, handler, tokens, cost = res.data, "llm", res.tokens, res.cost
        except (BudgetExceeded, LLMUnavailable, openai.APIError) as e:
            src.status = "queued"
            db.audit(s, "orchestrator", "queued", source=src.id, reason=str(e)[:200])
            return {"outcome": "queued", "source": src.id, "reason": str(e)[:200]}

        problems = validate(ext, src.received_at)
        outcome = state.apply(s, src, ext, problems)
        s.add(db.Trace(run_id=run_id, task_kind="extract", input_ref=src.id, handler=handler, tokens=tokens,
                       cost=cost, output_json=ext.model_dump(mode="json", exclude_none=True), accepted=not problems))
        src.status = "done"
        return {"outcome": outcome, "source": src.id, "handler": handler, "type": ext.type, "problems": problems,
                "extraction": ext}

    def drain(self) -> list[dict]:
        """Retry sources that were queued (budget exhausted, provider down)."""
        with db.Session() as s:
            results = [self.process(s, src) for src in
                       s.scalars(select(db.SourceRecord).where(db.SourceRecord.status == "queued")).all()]
            s.commit()
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

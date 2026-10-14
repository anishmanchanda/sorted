from sqlalchemy import select

from brain import agents, db
from brain.llm import BudgetExceeded
from brain.orchestrator import Orchestrator


def _rows(model):
    with db.Session() as s:
        return s.scalars(select(model)).all()


def test_full_fixture_run_with_perfect_extractor(fixtures, label_llm):
    orch = Orchestrator(llm=label_llm)
    outcomes = [orch.ingest(m)["outcome"] for m in fixtures]
    assert outcomes.count("dropped_otp") == 4
    assert len(_rows(db.SourceRecord)) == len(fixtures) - 4  # OTPs never stored
    obs = _rows(db.Obligation)
    # HDFC + Airtel SMS duplicate their emails; car insurance reminders repeat one fact; Sep BSES PDF = email
    assert outcomes.count("duplicate") == 6 + 6 + 3 + 1
    flagged = [o for o in obs if o.status == "flagged"]
    assert {o.provider for o in flagged} == {"ICICI Lombard"}  # policy schedule premium != renewal quote
    assert all(o.source_id for o in obs)
    assert {s.service: float(s.price) for s in _rows(db.Subscription)} == {"Netflix": 649.0, "Spotify": 139.0}
    assert [d.type for d in _rows(db.Document)] == ["puc"]
    traces = _rows(db.Trace)
    assert len(traces) == len(fixtures) - 4 and all(t.task_kind == "extract" for t in traces)


def test_prompt_injection_email_produces_no_action(fixtures, label_llm):
    """The injection email never reaches the LLM, writes no facts and triggers no action."""
    orch = Orchestrator(llm=label_llm)
    msg = next(m for m in fixtures if "injection" in m.raw_path)
    out = orch.ingest(msg)
    assert out["outcome"] == "ignored" and out["handler"] == "rule:injection_guard"
    assert label_llm.calls == []
    assert _rows(db.Obligation) == [] and _rows(db.Subscription) == []
    assert [a.action for a in _rows(db.AuditLog)] == ["suspicious_input"]


def test_no_agent_can_send_pay_forward_or_delete():
    tools = [t for cls in (agents.InboxAgent, agents.DocumentAgent, agents.ChatAgent, Orchestrator)
             for t in cls.TOOLS]
    assert not [t for t in tools if any(bad in t for bad in ("send", "pay", "forward", "delete", "email.write"))]


def test_budget_exhaustion_queues_then_drains(fixtures, label_llm):
    class Broke:
        def json(self, *a, **k):
            raise BudgetExceeded("daily token budget reached")

    msg = next(m for m in fixtures if "bses" in m.raw_path)
    assert Orchestrator(llm=Broke()).ingest(msg)["outcome"] == "queued"
    assert _rows(db.SourceRecord)[0].status == "queued" and _rows(db.Obligation) == []
    assert [r["outcome"] for r in Orchestrator(llm=label_llm).drain()] == ["open"]
    assert _rows(db.SourceRecord)[0].status == "done" and len(_rows(db.Obligation)) == 1


def test_failed_validation_flags_instead_of_dropping(fixtures, make_llm):
    bad = make_llm(lambda user, schema: {"type": "bill_due", "provider": "BSES", "amount": -5,
                                         "due_date": "2026-04-20"})
    msg = next(m for m in fixtures if "bses" in m.raw_path)
    out = Orchestrator(llm=bad).ingest(msg)
    ob = _rows(db.Obligation)[0]
    assert out["outcome"] == "flagged" and ob.confidence < 1 and "amount" in ob.note
    assert _rows(db.Trace)[0].accepted is False

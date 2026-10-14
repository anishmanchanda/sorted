"""Scheduler, planner, reply handlers and bot logic, offline."""

import uuid
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import select

from brain import db, notify, replies, scheduler
from brain.planner import PlannerAgent, plan_obligations
from brain.telegram_bot import due_text, respond


@pytest.fixture
def sent(monkeypatch):
    out = []
    monkeypatch.setattr(notify, "SINKS", [out.append])
    scheduler.get().remove_all_jobs()
    yield out
    scheduler.get().remove_all_jobs()


def _source(s, kind="email"):
    src = db.SourceRecord(kind=kind, sender="x", body_hash=uuid.uuid4().hex, received_at=datetime.now())
    s.add(src)
    s.flush()
    return src


def test_quiet_hours():
    assert scheduler.in_quiet_hours(time(23, 30), "22-07") and scheduler.in_quiet_hours(time(6, 59), "22-07")
    assert not scheduler.in_quiet_hours(time(7, 0), "22-07") and not scheduler.in_quiet_hours(time(13), "22-07")
    assert scheduler.after_quiet(datetime(2026, 10, 1, 23, 0), "22-07") == datetime(2026, 10, 2, 7, 0)
    assert scheduler.after_quiet(datetime(2026, 10, 2, 3, 0), "22-07") == datetime(2026, 10, 2, 7, 0)


def test_reminders_due_close_together_are_merged(sent, monkeypatch):
    monkeypatch.setenv("BRAIN_QUIET_HOURS", "0-0")  # never quiet in this test
    soon = scheduler.now() + timedelta(minutes=5)
    scheduler.create_reminder("Pay Airtel", soon, key="a")
    scheduler.fire_reminder("Pay HDFC")
    assert sent == ["Reminders:\n• Pay HDFC\n• Pay Airtel"]
    assert scheduler.get().get_job("a") is None


def test_quiet_hours_defer_instead_of_sending(sent, monkeypatch):
    monkeypatch.setenv("BRAIN_QUIET_HOURS", "22-07")
    monkeypatch.setattr(scheduler, "now", lambda: datetime(2026, 10, 1, 23, 0))
    scheduler.fire_reminder("Pay HDFC")
    assert sent == []
    [(run_at, text, _)] = scheduler.upcoming()
    assert text == "Pay HDFC" and run_at.replace(tzinfo=None) == datetime(2026, 10, 2, 7, 0)
    scheduler.fire_reminder("Server down", urgent=True)
    assert sent == ["Server down"]


def test_relative_reminder_for_new_obligation(sent):
    due = scheduler.now().date() + timedelta(days=10)
    with db.Session() as s:
        src = _source(s)
        s.add(db.Obligation(type="bill", provider="HDFC Bank", amount=13903.23, due_date=due, source_id=src.id))
        s.commit()
        src_id = src.id
    [job_id] = plan_obligations(src_id)
    job = scheduler.get().get_job(job_id)
    assert job.trigger.run_date.replace(tzinfo=None) == datetime.combine(due - timedelta(days=3), time(9))
    assert job.kwargs["text"].startswith("HDFC Bank bill ₹13,903.23 is due on")
    with db.Session() as s:  # a past due date gets no reminder
        src = _source(s)
        s.add(db.Obligation(type="bill", provider="Old", amount=1, due_date=date(2020, 1, 1), source_id=src.id))
        s.commit()
        assert plan_obligations(src.id) == []


def test_medicine_tracker_dose_log_and_refill_rule(sent, make_llm, monkeypatch):
    monkeypatch.setenv("BRAIN_QUIET_HOURS", "0-0")
    llm = make_llm(lambda user, schema: {"kind": "medication", "name": "thyroid tablet", "dose": "1 tablet",
                                         "times": ["08:00"], "stock": 6, "person": "Mom"})
    reply = PlannerAgent(llm).plan("Track Mom's thyroid tablet, 1 every morning, 6 left")
    assert reply.startswith("Tracking Mom's thyroid tablet: 1 tablet at 08:00 daily, 6 left")
    with db.Session() as s:
        med = s.scalar(select(db.Medication))
    job = scheduler.get().get_job(f"dose:{med.id}:08:00")
    assert str(job.trigger).startswith("cron[") and job.kwargs == {"medication_id": med.id}

    scheduler.fire_dose(med.id)  # 8 AM: template message, no LLM
    assert sent == ["Time for Mom's thyroid tablet (1 tablet). Reply 1 when taken."]
    assert replies.handle("1") == "Logged Mom's thyroid tablet. 5 left."
    assert sent[-1] == "Only 5 left of Mom's thyroid tablet. Time to order a refill."
    with db.Session() as s:
        assert s.get(db.Medication, med.id).stock == 5 and len(s.scalars(select(db.DoseLog)).all()) == 1
    assert len(llm.calls) == 1  # only the original request used the LLM


def test_paid_and_snooze(sent, monkeypatch):
    monkeypatch.setenv("BRAIN_QUIET_HOURS", "0-0")
    with db.Session() as s:
        src = _source(s)
        ob = db.Obligation(type="bill", provider="BSES Rajdhani", amount=959, due_date=date(2026, 10, 20),
                           source_id=src.id)
        s.add(ob)
        s.commit()
        ob_id = ob.id
    scheduler.fire_reminder("BSES Rajdhani bill is due", obligation_id=ob_id)
    assert replies.handle("snooze 1h").startswith("Snoozed until")
    assert [t for _, t, _ in scheduler.upcoming()] == ["BSES Rajdhani bill is due"]
    assert replies.handle("paid") == "Marked BSES Rajdhani ₹959.00 (due 20 Oct) as paid."
    with db.Session() as s:
        assert s.get(db.Obligation, ob_id).status == "paid"
    assert replies.handle("what's due?") is None


def test_due_text_and_routing(make_llm, monkeypatch):
    monkeypatch.setenv("BRAIN_TODAY", "2026-10-01")
    with db.Session() as s:
        src = _source(s)
        s.add(db.Obligation(type="bill", provider="HDFC Bank", amount=13903.23, due_date=date(2026, 10, 2),
                            source_id=src.id))
        s.add(db.Obligation(type="bill", provider="Later", amount=1, due_date=date(2026, 12, 2), source_id=src.id))
        s.commit()
    assert due_text() == "Due in the next 7 days:\nFri 02 Oct · HDFC Bank bill ₹13,903.23"

    class Orch:
        def ask(self, q):
            return f"chat:{q}"

    planner = PlannerAgent(make_llm(lambda user, schema: {"kind": "none"}))
    assert respond("when is my car insurance due?", Orch(), planner) == "chat:when is my car insurance due?"
    assert respond("remind me to call the plumber", Orch(), planner) == "chat:remind me to call the plumber"

"""Meeting requests, compiled chat questions and the simulation engine + web API, offline."""

import json
import re
import threading
import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from brain import actions, config, db, meetings, notify, query, scheduler, skills
from brain.orchestrator import Orchestrator
from brain.validate import Extraction

APPT_CODE = r'''
import re

def extract(text):
    if not re.search(r"appointment|doctor|meeting", text, re.I):
        raise ValueError("not about appointments")
    return {"intent": "appointments", "period": "this_month" if re.search(r"this month", text, re.I) else "upcoming"}
'''


def planner(text: str) -> dict:
    if m := re.search(r"between (.+) and (.+)$", text):
        return {"intent": "digest", "period": "range", "start": m.group(1), "end": m.group(2)}
    if any(w in text.lower() for w in ("appointment", "doctor", "meeting")):
        return {"intent": "appointments", "period": "this_month" if "this month" in text.lower() else "upcoming"}
    if any(w in text.lower() for w in ("pay", "due", "bill")):
        return {"intent": "due_items", "period": "next_14_days"}
    return {"intent": "unknown"}


@pytest.fixture
def smart_llm(label_llm, make_llm):
    """Extraction from labels, a keyword query planner, and a hand-written recogniser as the 'compiler'."""
    def answer(user, schema):
        name = schema.__name__
        if name == "Extraction":
            return label_llm.answer(user, schema)
        if name == "QuerySpec":
            return planner(user)
        if name == "CodeGen":
            return {"code": APPT_CODE}
        return {"answer": "free-form answer"}
    return make_llm(answer)


def test_meeting_request_pick_another_time_then_reply_only_with_permission(fixtures, label_llm, monkeypatch):
    asked = []
    monkeypatch.setattr(notify, "ASK_SINKS", [lambda text, acts: asked.append((text, acts))])
    monkeypatch.setenv("BRAIN_USER_NAME", "Rohan")
    scheduler.get().remove_all_jobs()
    msg = next(m for m in fixtures if "meeting_kitchen" in m.raw_path)
    out = Orchestrator(llm=label_llm).ingest(msg)
    sid = out["source"]
    assert out["type"] == "meeting_request" and out["outcome"] == "proposed"
    [(text, acts)] = asked
    assert "Meeting request from Ravi Kumar (Acme Infra)" in text
    assert [a for _, a in acts] == [f"meet:{sid}:yes", f"meet:{sid}:other", f"meet:{sid}:no"]
    monkeypatch.setattr(scheduler, "now", lambda: msg.received_at)
    assert actions.handle(acts[1][1])["awaiting_time"] == sid
    with db.Session() as s:
        proposed = meetings.start_of(meetings.obligation_for(s, sid))
    at = meetings.parse_when("Friday 5pm", proposed)
    assert (at.weekday(), at.hour) == (4, 17) and at > proposed
    assert meetings.parse_when("sounds good", proposed) is None
    res = actions.handle(f"meet:{sid}:at:{at:%Y-%m-%dT%H:%M}")
    assert "meet.google.com/" in res["meet"] and "calendar.google.com" in res["link"] and "BEGIN:VEVENT" in res["ics"]
    text, acts = res["followup"]
    assert "To: Ravi Kumar <" in text and "doesn't suit me" in text and res["meet"] in text
    with db.Session() as s:
        assert meetings.outbox(s) == []  # nothing goes out without the button
        assert meetings.start_of(meetings.obligation_for(s, sid)) == at
    assert actions.handle(acts[0][1])["sent"]["to"].startswith("Ravi Kumar")
    with db.Session() as s:
        [mail] = meetings.outbox(s)
    assert mail["subject"].startswith("Re: ") and mail["body"].endswith("Rohan")
    assert actions.handle(acts[0][1])["text"].startswith("Already")
    assert actions.handle(f"meet:{sid}:yes")["text"].startswith("Already accepted")
    assert {j.id for j in scheduler.get().get_jobs()} >= {f"meet:{1}:1d", f"meet:{1}:1h"}
    scheduler.get().remove_all_jobs()


def test_dues_and_updates_between_two_dates(fixtures, label_llm, smart_llm, monkeypatch):
    monkeypatch.setenv("BRAIN_TODAY", "2026-06-10")
    spec = query.normalize(query.QuerySpec(intent="digest", period="range", start="1st june", end="august"))
    assert (spec.start, spec.end) == ("2026-06-01", "2026-08-31")
    orch = Orchestrator(llm=label_llm)
    for m in fixtures[:25]:
        orch.ingest(m)
    with db.Session() as s:
        due = sorted(o.due_date for o in s.scalars(select(db.Obligation)) if o.due_date)
    q = f"give me all my dues and updates between {due[0]:%d %B} and {due[-1]:%d %B}"
    out = Orchestrator(llm=smart_llm).ask_detail(q)
    assert out["spec"]["intent"] == "digest" and out["spec"]["start"] == due[0].isoformat()
    assert out["answer"].startswith(f"Everything between {due[0].day} {due[0]:%b %Y}")
    assert "💳 Due (" in out["answer"] and "📨 Updates received (" in out["answer"]


def test_repeated_question_type_is_compiled_and_answered_without_llm(fixtures, label_llm, smart_llm, monkeypatch):
    monkeypatch.setenv("BRAIN_SHADOW_RUNS", "1")
    monkeypatch.setenv("BRAIN_TODAY", "2026-06-10")
    orch = Orchestrator(llm=smart_llm)
    for m in [m for m in fixtures if "apollo" in m.raw_path][:3]:
        orch.ingest(m)
    questions = ["Do I have any doctor appointments this month?", "Any appointments coming up?",
                 "When is my next doctor appointment?"]
    assert [orch.ask_detail(q)["handler"] for q in questions] == ["llm"] * 3
    with db.Session() as s:
        [res] = query.compile_pending(s, smart_llm)
        s.commit()
    assert (res["ability"], res["status"]) == ("query_appointments", "tested")
    actions.handle("approve:query_appointments")
    shadow = orch.ask_detail("Any doctor appointments this month?")
    assert shadow["handler"] == "llm" and "-> active" in shadow["event"]
    calls = len(smart_llm.calls)
    local = orch.ask_detail("Do I have a doctor appointment this month?")
    assert local["handler"] == "ability:query_appointments@v1" and len(smart_llm.calls) == calls
    assert local["answer"].startswith("You have") and "Apollo Clinic" in local["answer"]
    assert orch.ask_detail("what should I pay?")["handler"] == "llm"  # other intents still go to the LLM


def test_engine_and_web_api(tmp_path, make_llm, monkeypatch):
    from brain.sim import Engine
    from brain.web.server import create_app

    for var in ("BRAIN_TODAY", "BRAIN_DATE_OFFSET"):
        monkeypatch.setenv(var, "0")
    monkeypatch.setattr(scheduler, "now", scheduler.now)
    monkeypatch.setattr(notify, "SINKS", [])
    monkeypatch.setattr(notify, "ASK_SINKS", [])
    labels, current = {}, {}

    def answer(user, schema):
        if schema.__name__ == "Extraction":
            return {k: v for k, v in labels[current["sid"]].items() if k in Extraction.model_fields}
        return planner(user) if schema.__name__ == "QuerySpec" else {"answer": "ok"}

    llm = make_llm(answer)
    plain = llm.json

    def json_with_key(route, system, user, schema, run_id="", cache_key=None):
        current["sid"] = (cache_key or "").removeprefix("extract:")
        return plain(route, system, user, schema, run_id, cache_key)

    llm.json = json_with_key
    engine = Engine(llm=llm, data_dir=tmp_path)
    labels.update({(r := json.loads(line))["id"]: r for line in config.LABELS_PATH.read_text().splitlines()})
    client = TestClient(create_app(engine))
    st = client.get("/api/state").json()
    assert st["status"]["delivered"] == 0 and st["status"]["month"] == 1
    events = client.post("/api/step", json={"to": "month"}).json()["events"]
    assert sum(e["kind"] == "message" for e in events) > 5
    st = client.get("/api/state").json()
    assert st["stats"]["months"][0]["month"] == "Sim month 1" and st["stats"]["messages"] > 5
    rows = client.get("/api/messages").json()
    assert len(rows) == 81 and {r["status"] for r in rows} == {"delivered", "pending"}
    first = next(r for r in rows if r["status"] == "delivered" and r["kind"] == "email")
    assert "From:" in client.get(f"/api/messages/{first['id']}").json()["redacted"]
    assert client.post("/api/chat", json={"text": "any bills due?"}).json()["handler"] == "llm"
    sid = client.post("/api/messages", json={"sender": "Me <me@example.in>", "subject": "hi", "body": "test"}).json()
    assert sid["id"].endswith("_user1")
    assert client.post("/api/step", json={"to": "bogus"}).status_code == 400
    assert isinstance(client.get("/api/abilities").json(), list)


SHIP_CODE = r'''
import re

def extract(text):
    m = re.search(r"Shipment request: (.+?)\. Dispatch by (\d{4}-\d{2}-\d{2})", text)
    if not m:
        raise ValueError("layout changed")
    return {"type": "other", "category": "shipment_request", "provider": "Acme Logistics", "topic": m.group(1),
            "due_date": m.group(2), "currency": "INR"}
'''


def test_generated_data_new_kind_of_message_becomes_a_skill(tmp_path, make_llm, monkeypatch):
    """Generate synthetic mail -> it arrives -> Sorted notices a new category -> asks -> compiles -> acts."""
    from brain.sim import Engine

    for var in ("BRAIN_TODAY", "BRAIN_DATE_OFFSET"):
        monkeypatch.setenv(var, "0")
    monkeypatch.setattr(scheduler, "now", scheduler.now)
    monkeypatch.setattr(notify, "SINKS", [])
    monkeypatch.setattr(notify, "ASK_SINKS", [])
    batch = {}

    def answer(user, schema):
        name = schema.__name__
        if name == "GenBatch":
            return batch
        if name == "Extraction":
            m = re.search(r"Shipment request: (.+?)\. Dispatch by (\S+)\.", user)
            if m is None:
                return {"type": "ignore"}
            return {"type": "other", "category": "shipment_request", "provider": "Acme Logistics",
                    "topic": m.group(1), "due_date": m.group(2)}
        if name == "SkillPlan":
            return {"title": "Shipment requests", "action": "remind_before_due", "why": "Each has a dispatch date."}
        return {"code": SHIP_CODE}

    llm = make_llm(answer)
    engine = Engine(llm=llm, data_dir=tmp_path)
    t0 = engine.now()
    batch.update(label="shipment requests from Acme Logistics", messages=[
        {"sender": "Acme Logistics <orders@acme.example.in>", "subject": f"New shipment request #{n}",
         "body": f"Shipment request: {n * 10} cartons to Pune. Dispatch by {(t0 + timedelta(days=n + 5)).date()}.",
         "at": (t0 + timedelta(hours=n)).isoformat(timespec="minutes")} for n in range(1, 5)])
    out = engine.generate("a business sending shipment requests")
    assert out["later"] == 4 and len({r["id"] for r in engine.dataset() if r["added"]}) == 4
    for _ in range(3):
        engine.step("next")
    [ask] = engine.status()["pending_actions"]
    assert "New kind of message: Shipment requests" in ask["title"]
    assert ask["actions"][0][1] == "skill:shipment_request:yes"
    with db.Session() as s:  # nothing compiled for the new category until the user agrees
        assert skills.scan(s) == [] and not s.scalars(select(db.Ability).where(db.Ability.kind == "parser")).all()
    engine.act("skill:shipment_request:yes")
    for _ in range(100):
        if any(e["kind"] == "compile" for e in engine.feed):
            break
        time.sleep(0.05)
    with engine.lock:
        compiled = [e for e in engine.feed if e["kind"] == "compile"]
    assert compiled and "acme_example_in_shipment_request v1 -> tested" in compiled[0]["title"]
    actions.handle("approve:acme_example_in_shipment_request")
    engine.step("next")  # the 4th one: shadow run next to the LLM, and the skill's reminder is scheduled
    assert any(j.id.startswith("skill:") for j in scheduler.get().get_jobs())
    assert any(a["kind"] == "skill" and a["status"] == "active" for a in engine.abilities())
    scheduler.get().remove_all_jobs()
    assert threading.active_count() >= 1


def test_autopilot_runs_the_whole_demo_saying_yes(tmp_path, make_llm, monkeypatch):
    """/run: six months unattended, month chapters and recaps, meetings booked and replies sent automatically."""
    from brain.llm import LLMUnavailable
    from brain.sim import Engine

    for var in ("BRAIN_TODAY", "BRAIN_DATE_OFFSET"):
        monkeypatch.setenv(var, "0")
    monkeypatch.setattr(scheduler, "now", scheduler.now)
    monkeypatch.setattr(notify, "SINKS", [])
    monkeypatch.setattr(notify, "ASK_SINKS", [])
    labels = {(r := json.loads(line))["id"]: r for line in config.LABELS_PATH.read_text().splitlines()}
    current = {}

    def answer(user, schema):
        if schema.__name__ == "Extraction":
            return {k: v for k, v in labels[current["sid"]].items() if k in Extraction.model_fields}
        if schema.__name__ == "QuerySpec":
            return planner(user)
        raise LLMUnavailable("offline test: no compiler")  # compiles stay candidates; the AI keeps the work

    llm = make_llm(answer)
    plain = llm.json

    def json_with_key(route, system, user, schema, run_id="", cache_key=None):
        current["sid"] = (cache_key or "").removeprefix("extract:")
        return plain(route, system, user, schema, run_id, cache_key)

    llm.json = json_with_key
    engine = Engine(llm=llm, data_dir=tmp_path)
    seen = []
    engine.listeners.append(seen.append)
    engine.delay = 0
    engine._autopilot(generate=False)
    titles = [e["title"] for e in seen if e["kind"] == "chapter"]
    assert [f"Sim month {n} begins" in " ".join(titles) for n in range(1, 7)] == [True] * 6
    assert sum(t.endswith("recap") for t in titles) == 6 and titles[-1] == "🏁 Demo complete"
    assert engine.now() >= engine.end() and engine.status()["pending_actions"] == []
    months = engine.months()
    assert [m["status"] for m in months] == ["done"] * 6 and sum(m["messages"] for m in months) > 70
    assert sum(m["meetings"] for m in months) >= 1 and sum(m["replies"] for m in months) >= 1
    recaps = [e["detail"] for e in seen if e["kind"] == "chapter" and e["title"].endswith("recap")]
    assert any("Highlights:" in r for r in recaps)  # offline the compiler is down: "Not yet: code for … failed"
    assert any("⏳ Not yet: code for HDFC Bank bill emails" in h for m in months for h in m["highlights"])
    assert engine.set_speed("fast") == "fast" and engine.delay < 1 and engine.set_speed("bogus") == "fast"
    meets = [e for e in seen if e["kind"] == "action" and e["detail"].startswith("meet:")]
    assert meets and all(e.get("handler") == "autopilot" for e in meets)
    scheduler.get().remove_all_jobs()

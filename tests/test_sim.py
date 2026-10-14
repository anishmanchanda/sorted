"""The demo's synthetic timeline: Sim-month ids, dates relative to the run date, replay across date shifts."""

import hashlib
import json
from datetime import date, datetime

from pydantic import BaseModel

from brain import db, samples, score
from brain.llm import LLM, shift_dates
from brain.messages import sim_sample


def test_generated_timeline_ends_on_the_given_date(tmp_path):
    end = date(2031, 3, 15)
    n = samples.generate(tmp_path / "s", tmp_path / "labels.jsonl", end)
    labels = [json.loads(line) for line in (tmp_path / "labels.jsonl").read_text().splitlines()]
    assert n == len(labels) == 76
    assert all(sim_sample(lab["id"] + ".eml") for lab in labels)  # every id is Sim-month prefixed
    rows = [json.loads(line) for line in (tmp_path / "s" / "sms" / "sms.jsonl").read_text().splitlines()]
    last = max(datetime.fromisoformat(r["received_at"]).date() for r in rows)
    assert last <= end and (end - last).days < 31
    shifted = {lab["id"]: lab["due_date"] for lab in labels}
    assert shifted["m6_youtube_price"] > end.isoformat()  # the pending price change is in the future


def test_sim_sample_and_score_periods():
    assert sim_sample("data/demo/samples/email/m6_hdfc_cc.eml") == ("m6_hdfc_cc", 6)
    assert sim_sample("data/samples/sms/sms.jsonl#sms_m2_airtel") == ("sms_m2_airtel", 2)
    assert sim_sample("imap:INBOX/42") is None
    with db.Session() as s:
        for path in ("data/demo/samples/email/m2_bses.eml", "imap:INBOX/1"):
            src = db.SourceRecord(kind="email", sender="x", body_hash=path, received_at=datetime(2026, 10, 3),
                                  raw_path=path)
            s.add(src)
            s.flush()
            s.add(db.Trace(run_id="r", task_kind="extract", input_ref=src.id, handler="llm"))
        s.commit()
        assert [r["month"] for r in score.monthly(s)] == ["2026-10", "Sim month 2"]


class Out(BaseModel):
    due_date: date
    amount: float


def test_replay_by_cache_key_moves_dates_with_the_timeline(tmp_path, monkeypatch):
    rec = {"data": {"due_date": "2026-05-02", "amount": 10.0}, "tokens": 5, "cost": 0.0, "model": "m",
           "date_offset": 0}
    name = hashlib.sha256(json.dumps(["small", "sys", "Out", "extract:m1_x"]).encode()).hexdigest()
    (tmp_path / f"{name}.json").write_text(json.dumps(rec))
    monkeypatch.setenv("BRAIN_DATE_OFFSET", "30")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    res = LLM(cache_dir=tmp_path).json("small", "sys", "any prompt, dates changed", Out, cache_key="extract:m1_x")
    assert res.replayed and res.data.due_date == date(2026, 6, 1) and res.data.amount == 10.0
    assert shift_dates({"a": ["2026-01-31T09:00:00"], "b": "x 2026-01-31"}, 1) == \
        {"a": ["2026-02-01T09:00:00"], "b": "x 2026-01-31"}

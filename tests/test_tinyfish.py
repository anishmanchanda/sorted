"""TinyFish adapter, fully offline: HTTP is mocked, Agent runs replay recorded fixtures."""

import json
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select

from brain import db
from brain.sources import tinyfish as tf

RECORDED = next(tf.FIXTURES.glob("agent_*.json"))


def _resp(payload):
    return SimpleNamespace(json=lambda: payload, raise_for_status=lambda: None)


def test_not_configured_is_a_clear_message(monkeypatch):
    monkeypatch.setenv("TINYFISH_API_KEY", "")
    monkeypatch.setenv("TINYFISH_LIVE", "1")
    with pytest.raises(tf.NotConfigured, match="TINYFISH_API_KEY"):
        tf.fetch(["https://example.com"])
    with pytest.raises(tf.NotConfigured):
        tf.agent_run("https://example.com", "anything")


def test_agent_never_goes_live_by_default(monkeypatch):
    monkeypatch.setenv("TINYFISH_LIVE", "0")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("Agent API must not be called"))
    with pytest.raises(tf.NotConfigured, match="TINYFISH_LIVE=0"):
        tf.agent_run("https://unrecorded.example", "goal")


def test_recorded_agent_run_replays_and_is_stored_as_trace(monkeypatch):
    monkeypatch.setenv("TINYFISH_LIVE", "0")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("no live call during replay"))
    rec = json.loads(RECORDED.read_text())
    out = tf.portal(rec["url"], rec["goal"], schema=tf.PRICE_SCHEMA)
    assert out["replayed"] and out["result"] == rec["response"]["result"]
    with db.Session() as s:
        trace = s.scalar(select(db.Trace))
        assert (trace.task_kind, trace.handler, trace.output_json) == ("portal", "tinyfish:agent", out["result"])


def test_bill_portal_result_becomes_an_obligation(monkeypatch):
    monkeypatch.setenv("TINYFISH_LIVE", "1")
    monkeypatch.setenv("TINYFISH_API_KEY", "k")
    sent = {}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        return _resp({"run_id": "r1", "status": "COMPLETED", "num_of_steps": 4,
                      "result": {"provider": "Demo Power", "amount_due": 1234.5, "due_date": "2026-11-20"}})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(tf, "datetime", SimpleNamespace(now=lambda: __import__("datetime").datetime(2026, 11, 1)))
    out = tf.portal("https://bills.example/acct", "get the amount due and due date")
    assert sent["url"] == tf.AGENT_URL and sent["headers"] == {"X-API-Key": "k"}
    assert sent["body"]["output_schema"] == tf.BILL_SCHEMA and out["outcome"] == "open"
    assert out["usage"] == "TinyFish usage: {'num_of_steps': 4}"
    with db.Session() as s:
        ob = s.scalar(select(db.Obligation))
        assert (ob.provider, float(ob.amount), str(ob.due_date)) == ("Demo Power", 1234.5, "2026-11-20")


def test_fetch_message_flows_like_email(monkeypatch):
    monkeypatch.setenv("TINYFISH_API_KEY", "k")
    page = {"url": "https://x.example/bill", "final_url": "https://x.example/bill", "title": "Your bill",
            "text": "Amount due ₹1,178.82 by 20 Oct 2026"}
    monkeypatch.setattr(httpx, "post", lambda url, headers, json, timeout: _resp({"results": [page], "errors": []}))
    msg = tf.fetch_message("https://x.example/bill")
    assert (msg.kind, msg.sender, msg.subject) == ("web", "x.example", "Your bill")
    assert tf.price_on_page(msg.body, 1178.82) and not tf.price_on_page(msg.body, 1178)
    assert tf.price_on_page("now ₹649/month", 649) and not tf.price_on_page("₹6,499", 649)

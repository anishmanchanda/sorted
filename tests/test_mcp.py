import asyncio
import uuid
from datetime import date, datetime

import pytest
from starlette.testclient import TestClient

from brain import db, mcp_server


def _seed():
    with db.Session() as s:
        src = db.SourceRecord(kind="email", sender="HDFC Bank <emailstatements.cards@hdfcbank.net>",
                              subject="Your HDFC Bank Credit Card Statement", body_hash=uuid.uuid4().hex,
                              received_at=datetime(2026, 9, 12), raw_path="data/samples/email/2026-09_hdfc_cc.eml")
        s.add(src)
        s.flush()
        ob = db.Obligation(type="bill", provider="HDFC Bank", amount=13903.23, due_date=date(2026, 10, 2),
                           source_id=src.id)
        s.add(ob)
        s.add(db.Ability(name="hdfc", version=1, status="tested", code="def extract(text):\n    return {}\n"))
        s.commit()
        return ob.id


def test_tools_resources_and_prompts_are_registered():
    tools = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
    assert tools == {"get_upcoming", "search_obligations", "get_obligation", "mark_paid", "create_reminder",
                     "list_abilities", "run_ability", "get_privacy_score"}
    assert {p.name for p in asyncio.run(mcp_server.server.list_prompts())} == {"weekly_review",
                                                                                "what_do_i_owe_this_month"}
    assert {str(r.uri) for r in asyncio.run(mcp_server.server.list_resources())} == {"sorted://profile",
                                                                                     "sorted://digest"}


def test_read_tools(monkeypatch):
    monkeypatch.setenv("BRAIN_TODAY", "2026-10-01")
    ob_id = _seed()
    assert [o["provider"] for o in mcp_server.get_upcoming(7)] == ["HDFC Bank"]
    assert mcp_server.get_upcoming(7, type="renewal") == []
    assert mcp_server.search_obligations("hdfc")[0]["id"] == ob_id
    full = mcp_server.get_obligation(ob_id)
    assert full["source"]["link"].endswith("2026-09_hdfc_cc.eml") and full["amount"] == 13903.23
    assert "HDFC Bank bill ₹13,903.23" in mcp_server.digest()


def test_write_tools_are_logged_and_scoped(monkeypatch):
    ob_id = _seed()
    monkeypatch.setenv("BRAIN_MCP_SCOPE", "read")
    with pytest.raises(PermissionError):
        mcp_server.mark_paid(ob_id)
    monkeypatch.setenv("BRAIN_MCP_SCOPE", "read-write")
    assert mcp_server.mark_paid(ob_id)["status"] == "paid"
    job = mcp_server.create_reminder("Renew PUC", "2030-11-05T10:00")
    assert job["when"] == "2030-11-05T10:00:00"
    with db.Session() as s:
        actions = [a.action for a in s.query(db.AuditLog).filter_by(actor="mcp")]
    assert actions == ["mark_paid", "create_reminder"]


def test_run_ability_only_runs_active_abilities():
    _seed()
    with pytest.raises(ValueError, match="no active ability"):
        mcp_server.run_ability("hdfc", "anything")


def test_http_requires_bearer_token(monkeypatch):
    monkeypatch.setenv("BRAIN_MCP_TOKEN", "s3cret")
    client = TestClient(mcp_server.http_app())
    assert client.post("/mcp", json={}).status_code == 401
    assert client.post("/mcp", json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401

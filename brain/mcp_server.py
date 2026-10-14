"""Brain MCP server (official MCP Python SDK): Sorted's state and abilities for Claude Desktop, Cursor or any
MCP client, so they answer from typed state instead of re-reading your inbox.

stdio (Claude Desktop / Cursor): `make mcp`.
Streamable HTTP: `uv run python -m brain.mcp_server --http` with BRAIN_MCP_TOKEN (bearer) and
BRAIN_MCP_SCOPE=read|read-write. Write tools are audit-logged; run_ability only runs `active` abilities, sandboxed.
"""

import json
import secrets
import sys
from datetime import datetime, timedelta

from mcp.server.mcpserver import MCPServer
from pydantic import ValidationError
from sqlalchemy import func, select

from brain import config, db, scheduler, score
from brain.redact import redact
from brain.state import provider_match

server = MCPServer(
    "sorted",
    instructions="Sorted knows the user's bills, renewals, premiums, subscriptions, appointments, documents and "
                 "medicines. Every fact has a source link. Amounts are INR. Write tools are logged.",
)


def _require_write() -> None:
    if config.env("BRAIN_MCP_SCOPE", "read-write") != "read-write":
        raise PermissionError("this MCP server is read-only (BRAIN_MCP_SCOPE=read)")


def _ob(o: db.Obligation) -> dict:
    return {"id": o.id, "type": o.type, "provider": o.provider, "amount": float(o.amount) if o.amount else None,
            "currency": o.currency, "due_date": o.due_date.isoformat() if o.due_date else None, "status": o.status,
            "confidence": o.confidence, "note": o.note or None, "source_id": o.source_id}


@server.tool()
def get_upcoming(days: int = 7, type: str | None = None) -> list[dict]:
    """Unpaid bills, premiums, renewals, subscriptions and appointments due in the next `days` days.
    `type` filters to one of: bill, premium, renewal, subscription, meeting."""
    today = config.today()
    with db.Session() as s:
        q = select(db.Obligation).where(db.Obligation.status != "paid",
                                        db.Obligation.due_date.between(today, today + timedelta(days=days)))
        if type:
            q = q.where(db.Obligation.type == type)
        return [_ob(o) for o in s.scalars(q.order_by(db.Obligation.due_date))]


@server.tool()
def search_obligations(query: str) -> list[dict]:
    """Find obligations by provider or type, e.g. "HDFC", "insurance", "netflix"."""
    with db.Session() as s:
        rows = s.scalars(select(db.Obligation).order_by(db.Obligation.due_date.desc())).all()
    q = query.lower()
    return [_ob(o) for o in rows if provider_match(o.provider, query) or q in o.type][:25]


@server.tool()
def get_obligation(id: int) -> dict:
    """One obligation with its source (the email, SMS, PDF or web page it came from)."""
    with db.Session() as s:
        o = s.get(db.Obligation, id)
        if o is None:
            raise ValueError(f"no obligation {id}")
        src = s.get(db.SourceRecord, o.source_id)
        return {**_ob(o), "source": {"kind": src.kind, "sender": src.sender, "subject": src.subject,
                                     "received_at": src.received_at.isoformat(), "link": src.raw_path}}


@server.tool()
def mark_paid(id: int) -> dict:
    """Mark an obligation as paid (write, audit-logged)."""
    _require_write()
    with db.Session() as s:
        o = s.get(db.Obligation, id)
        if o is None:
            raise ValueError(f"no obligation {id}")
        o.status = "paid"
        db.audit(s, "mcp", "mark_paid", obligation=id)
        s.commit()
        return _ob(o)


@server.tool()
def create_reminder(text: str, when: str) -> dict:
    """Schedule a reminder message to the user at `when` (ISO datetime, IST). Write, audit-logged. Fires with no AI."""
    _require_write()
    run_at = datetime.fromisoformat(when).replace(tzinfo=None)
    job_id = scheduler.create_reminder(text[:300], run_at, key=f"mcp:{secrets.token_hex(4)}")
    with db.Session() as s:
        db.audit(s, "mcp", "create_reminder", text=text[:300], when=run_at.isoformat(), job=job_id)
        s.commit()
    return {"job_id": job_id, "text": text[:300], "when": run_at.isoformat()}


@server.tool()
def list_abilities() -> list[dict]:
    """Compiled abilities (local parsers the Brain wrote for itself) with status and health stats."""
    from brain.compiler import registry

    with db.Session() as s:
        return [{"name": a.name, "version": a.version, "status": a.status, "trigger": a.trigger_json,
                 "permissions": a.permissions, "runs": a.runs, "failures": a.failures,
                 "shadow_matches": a.shadow_matches, "last_error": a.last_error or None} for a in registry.listing(s)]


@server.tool()
def run_ability(name: str, input: str) -> dict:
    """Run an ACTIVE ability on text (e.g. a pasted bill email). Sandboxed, no LLM, no network."""
    from brain.compiler import sandbox
    from brain.validate import Extraction

    with db.Session() as s:
        ab = s.scalars(select(db.Ability).where(db.Ability.name == name, db.Ability.status == "active")
                       .order_by(db.Ability.version.desc())).first()
        if ab is None:
            raise ValueError(f"no active ability named {name!r}")
        r = sandbox.run(ab.code, [redact(input)], timeout=10)[0]
        db.audit(s, "mcp", "run_ability", ability=name, version=ab.version, ok=r["ok"])
        s.commit()
    if not r["ok"]:
        return {"ok": False, "error": r["error"]}
    try:
        return {"ok": True, "ability": f"{name}@v{ab.version}",
                "output": Extraction.model_validate(r["value"]).model_dump(mode="json", exclude_none=True)}
    except ValidationError as e:
        return {"ok": False, "error": f"output failed schema validation: {e.errors()[0]['msg']}"}


@server.tool()
def get_privacy_score() -> dict:
    """Share of messages handled by local code (no LLM) per month, plus LLM calls and cost per message."""
    with db.Session() as s:
        months = score.monthly(s)
    tasks = sum(m["tasks"] for m in months)
    return {"overall_privacy": sum(m["local"] for m in months) / tasks if tasks else None, "months": months}


@server.resource("sorted://profile", mime_type="application/json")
def profile() -> str:
    """A compact summary of what Sorted tracks."""
    with db.Session() as s:
        counts = dict(s.execute(select(db.Obligation.type, func.count()).group_by(db.Obligation.type)).all())
        subs = s.scalars(select(db.Subscription)).all()
        meds = s.scalars(select(db.Medication)).all()
        docs = s.scalars(select(db.Document)).all()
        return json.dumps({
            "obligations_by_type": counts,
            "subscriptions": [{"service": x.service, "price": float(x.price)} for x in subs],
            "medications": [{"name": m.name, "person": m.person, "times": m.times, "stock": m.stock} for m in meds],
            "documents": [{"type": d.type, "expiry": d.expiry.isoformat() if d.expiry else None} for d in docs],
        })


@server.resource("sorted://digest", mime_type="text/plain")
def digest() -> str:
    """This month's digest: what is due, subscription prices, price changes and the privacy score."""
    today = config.today()
    start = today.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    with db.Session() as s:
        due = s.scalars(select(db.Obligation).where(db.Obligation.due_date >= start, db.Obligation.due_date < end)
                        .order_by(db.Obligation.due_date)).all()
        subs = s.scalars(select(db.Subscription)).all()
        changes = s.scalars(select(db.AuditLog).where(db.AuditLog.action == "subscription_price_increase")).all()
        months = score.monthly(s)
    lines = [f"Digest for {today:%B %Y}", "", "Due this month:"]
    lines += [f"- {o.due_date:%d %b} {o.provider} {o.type}" + (f" ₹{float(o.amount):,.2f}" if o.amount else "")
              + f" [{o.status}]" for o in due]
    lines += ["", "Subscriptions:"] + [f"- {x.service}: ₹{float(x.price):,.0f}/month" for x in subs]
    lines += ["", "Price increases seen:"] + [f"- {c.detail.get('service')} -> ₹{c.detail.get('new_price')}"
                                              for c in changes]
    if months:
        lines += ["", f"Privacy score last month: {100 * months[-1]['privacy']:.0f}% handled by local code"]
    return "\n".join(lines)


@server.prompt()
def weekly_review() -> str:
    """Review the coming week."""
    return ("Give me my weekly admin review. Call get_upcoming(days=7) and list each item with its date and amount, "
            "flag anything with status 'flagged' and explain the note, mention medicines low on stock from the "
            "sorted://profile resource, and end with one line on my privacy score from get_privacy_score.")


@server.prompt()
def what_do_i_owe_this_month() -> str:
    """Total of what is due this month."""
    return ("What do I owe this month? Read the sorted://digest resource, list every unpaid item due this month with "
            "its amount, give the total in rupees, and offer to mark_paid anything I say I've already paid.")


class BearerAuth:
    """ASGI middleware: Streamable HTTP requires `Authorization: Bearer <BRAIN_MCP_TOKEN>`."""

    def __init__(self, app, token: str):
        self.app, self.expected = app, f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            got = dict(scope["headers"]).get(b"authorization", b"")
            if not secrets.compare_digest(got, self.expected):
                from starlette.responses import JSONResponse

                await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def http_app():
    token = config.env("BRAIN_MCP_TOKEN")
    if not token:
        raise SystemExit("Set BRAIN_MCP_TOKEN to serve MCP over HTTP.")
    return BearerAuth(server.streamable_http_app(), token)


def main() -> None:
    db.init_db()
    if "--http" in sys.argv:
        import uvicorn

        host, port = config.env("BRAIN_MCP_HOST", "127.0.0.1"), int(config.env("BRAIN_MCP_PORT", "8765"))
        uvicorn.run(http_app(), host=host, port=port)
    else:
        server.run()  # stdio


if __name__ == "__main__":
    main()

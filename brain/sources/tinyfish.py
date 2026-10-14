"""TinyFish adapter (https://docs.tinyfish.ai): Fetch, Agent and Search APIs over plain HTTPS, `X-API-Key` auth.

- Fetch (free): read a page the user points at (a bill page, a public pricing page). The page becomes a normal
  `web` Message and goes through the same pipeline as email (redaction, agents, validation, compiler).
- Agent (uses credits): a natural-language goal on a portal with an `output_schema`. Every run is stored as a
  trace (task_kind="portal") so it can graduate like any other task. By default (TINYFISH_LIVE=0) runs are
  replayed from tests/fixtures/tinyfish/; set TINYFISH_LIVE=1 for a real run (recorded with --record).
- Search (free): find a biller's official site.
Without TINYFISH_API_KEY every call raises NotConfigured with a clear message; callers skip gracefully.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from brain import config, db, state
from brain.messages import Message
from brain.redact import redact
from brain.validate import Extraction, validate

FETCH_URL = "https://api.fetch.tinyfish.ai"
AGENT_URL = "https://agent.tinyfish.ai/v1/automation/run"
SEARCH_URL = "https://api.search.tinyfish.ai"
FIXTURES = config.ROOT / "tests" / "fixtures" / "tinyfish"

BILL_SCHEMA = {  # Agent API structured-output schema for a bill / renewal page
    "type": "object",
    "properties": {
        "provider": {"type": "string"},
        "amount_due": {"type": "number"},
        "due_date": {"type": "string", "description": "YYYY-MM-DD"},
        "currency": {"type": "string"},
    },
    "required": ["provider", "amount_due", "due_date"],
}


PRICE_SCHEMA = {  # confirm a subscription's public price
    "type": "object",
    "properties": {
        "provider": {"type": "string"},
        "plan": {"type": "string"},
        "price": {"type": "number"},
        "currency": {"type": "string"},
    },
    "required": ["provider", "plan", "price", "currency"],
}


class NotConfigured(RuntimeError):
    pass


def _key() -> str:
    key = config.env("TINYFISH_API_KEY")
    if not key:
        raise NotConfigured("TinyFish is not configured: set TINYFISH_API_KEY in .env (skipping web sources)")
    return key


def _usage(resp: dict) -> str:
    usage = {k: resp[k] for k in ("usage", "credits", "credits_used", "num_of_steps") if resp.get(k) is not None}
    return f"TinyFish usage: {usage}" if usage else ""


def fetch(urls: list[str], fmt: str = "markdown", ttl: int | None = None) -> list[dict]:
    body: dict = {"urls": urls, "format": fmt}
    if ttl is not None:
        body["ttl"] = ttl
    r = httpx.post(FETCH_URL, headers={"X-API-Key": _key()}, json=body, timeout=150)
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(f"TinyFish fetch errors: {data['errors']}")
    return data["results"]


def fetch_message(url: str) -> Message:
    """A web page as a Message, so it flows through the same ingestion pipeline as email."""
    page = fetch([url])[0]
    return Message("web", urlparse(page.get("final_url") or url).netloc, page.get("title") or url,
                   page.get("text") or "", datetime.now(), url)


def price_on_page(text: str, price: float) -> bool:
    """Does the page show this price (e.g. to confirm a price-change email against the public pricing page)?"""
    p = f"{price:,.0f}" if float(price).is_integer() else f"{price:,.2f}"
    return bool(re.search(rf"(?:₹|Rs\.?|INR)\s?{re.escape(p)}(?![\d,]|\.\d)", text))


def search(query: str, location: str = "IN", language: str = "en") -> list[dict]:
    r = httpx.get(SEARCH_URL, headers={"X-API-Key": _key()},
                  params={"query": query, "location": location, "language": language}, timeout=15)
    r.raise_for_status()
    return r.json().get("results", [])


def _fixture(url: str, goal: str):
    return FIXTURES / f"agent_{hashlib.sha256(f'{url}|{goal}'.encode()).hexdigest()[:12]}.json"


def agent_run(url: str, goal: str, output_schema: dict | None = None, record: bool = False) -> tuple[dict, bool]:
    """(response, replayed). Never called in tests or loops; live only with TINYFISH_LIVE=1."""
    fixture = _fixture(url, goal)
    if config.env("TINYFISH_LIVE", "0") != "1":
        if fixture.exists():
            return json.loads(fixture.read_text())["response"], True
        raise NotConfigured("TINYFISH_LIVE=0 and no recorded Agent response for this url+goal. "
                            "Set TINYFISH_LIVE=1 for a real run (uses TinyFish credits).")
    body = {"url": url, "goal": goal, "browser_profile": "lite"}
    if output_schema:
        body["output_schema"] = output_schema
    r = httpx.post(AGENT_URL, headers={"X-API-Key": _key()}, json=body, timeout=180)
    r.raise_for_status()
    resp = r.json()
    if record:
        FIXTURES.mkdir(parents=True, exist_ok=True)
        fixture.write_text(json.dumps({"url": url, "goal": goal, "recorded_at": f"{datetime.now():%Y-%m-%d}",
                                       "response": resp}, indent=1))
    return resp, False


def portal(url: str, goal: str, schema: dict | None = None, record: bool = False) -> dict:
    """Run a goal on a portal page and store the run as a trace (task_kind="portal") like any other task.
    A result with amount_due + due_date also becomes a bill obligation in state."""
    resp, replayed = agent_run(url, goal, schema or BILL_SCHEMA, record=record)
    result = resp.get("result") or {}
    if resp.get("status") != "COMPLETED" or not result:
        return {"outcome": "failed", "error": resp.get("error"), "replayed": replayed, "result": result}
    now = datetime.now()
    body_hash = hashlib.sha256(f"{url}|{goal}|{json.dumps(result, sort_keys=True)}".encode()).hexdigest()
    ext, problems, outcome = None, [], "recorded"
    with db.Session() as s:
        src = s.scalar(select(db.SourceRecord).where(db.SourceRecord.body_hash == body_hash))
        if src is None:
            src = db.SourceRecord(kind="web", sender=urlparse(url).netloc, subject=redact(goal)[:500],
                                  body_hash=body_hash, received_at=now, raw_path=url,
                                  text=redact(f"URL: {url}\nGOAL: {goal}\nRESULT: {json.dumps(result)}"))
            s.add(src)
            s.flush()
            if result.get("amount_due") is not None and result.get("due_date"):
                ext = Extraction(type="bill_due", provider=result.get("provider"), amount=result["amount_due"],
                                 currency=result.get("currency") or "INR", due_date=result["due_date"])
                problems = validate(ext, now)
                outcome = state.apply(s, src, ext, problems)
        else:
            outcome = "already_seen"
        s.add(db.Trace(run_id=resp.get("run_id") or uuid.uuid4().hex[:12], task_kind="portal",
                       handler="tinyfish:agent", input_ref=src.id, accepted=not problems, output_json=result))
        s.commit()
    return {"outcome": outcome, "result": result, "extraction": ext, "problems": problems, "replayed": replayed,
            "usage": _usage(resp)}

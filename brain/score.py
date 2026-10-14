"""Privacy score (share of tasks handled by local code) and cost per message, per period.

Real usage is grouped by calendar month; the demo's synthetic samples are grouped as "Sim month 1-6".

A task is one `extract` trace. Local = handled without an LLM call (compiled ability or rule).
Cost includes every LLM call attributed to that month's messages, compile and repair calls too.
"""

from collections import defaultdict

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from brain import db
from brain.messages import sim_sample


def period(raw_path: str, received) -> str:
    sim = sim_sample(raw_path)
    return f"Sim month {sim[1]}" if sim else f"{received:%Y-%m}"


def monthly(s) -> list[dict]:
    rows = s.execute(
        select(db.Trace.task_kind, db.Trace.handler, db.Trace.tokens, db.Trace.cost, db.SourceRecord.received_at,
               db.SourceRecord.raw_path)
        .join(db.SourceRecord, db.Trace.input_ref == db.SourceRecord.id)
    ).all()
    m = defaultdict(lambda: {"tasks": 0, "local": 0, "llm_calls": 0, "tokens": 0, "cost": 0.0})
    for kind, handler, tokens, cost, received, raw_path in rows:
        r = m[period(raw_path, received)]
        if kind == "extract":
            r["tasks"] += 1
            r["local"] += handler != "llm"
        r["llm_calls"] += handler == "llm"
        r["tokens"] += tokens
        r["cost"] += cost
    out = []
    for month, r in sorted(m.items()):
        if not r["tasks"]:
            continue  # e.g. a month with only TinyFish portal runs
        tasks = r["tasks"] or 1
        out.append({"month": month, **r, "privacy": r["local"] / tasks, "cost_per_message": r["cost"] / tasks})
    return out


def table(rows: list[dict]) -> str:
    lines = ["| period | messages | local code | LLM calls | tokens | privacy score | cost / message (USD) |",
             "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['month']} | {r['tasks']} | {r['local']} | {r['llm_calls']} | {r['tokens']} | "
              f"{100 * r['privacy']:.0f}% | {r['cost_per_message']:.5f} |" for r in rows]
    return "\n".join(lines)


def summary(db_url: str | None = None) -> str:
    """Score table for the live DB, or for another DB (e.g. config.DEMO_DB_URL)."""
    session = db.Session if db_url is None else sessionmaker(create_engine(db_url))
    with session() as s:
        rows = monthly(s)
    return table(rows) if rows else "No messages handled yet."

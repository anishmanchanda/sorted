"""Privacy score (share of tasks handled by local code) and cost per message, per simulated month.

A task is one `extract` trace. Local = handled without an LLM call (compiled ability or rule).
Cost includes every LLM call attributed to that month's messages, compile and repair calls too.
"""

from collections import defaultdict

from sqlalchemy import select

from brain import db


def monthly(s) -> list[dict]:
    rows = s.execute(
        select(db.Trace.task_kind, db.Trace.handler, db.Trace.tokens, db.Trace.cost, db.SourceRecord.received_at)
        .join(db.SourceRecord, db.Trace.input_ref == db.SourceRecord.id)
    ).all()
    m = defaultdict(lambda: {"tasks": 0, "local": 0, "llm_calls": 0, "tokens": 0, "cost": 0.0})
    for kind, handler, tokens, cost, received in rows:
        r = m[f"{received:%Y-%m}"]
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
    lines = ["| month | messages | local code | LLM calls | tokens | privacy score | cost / message (USD) |",
             "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['month']} | {r['tasks']} | {r['local']} | {r['llm_calls']} | {r['tokens']} | "
              f"{100 * r['privacy']:.0f}% | {r['cost_per_message']:.5f} |" for r in rows]
    return "\n".join(lines)


def summary() -> str:
    with db.Session() as s:
        rows = monthly(s)
    return table(rows) if rows else "No messages handled yet."

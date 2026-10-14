"""`brain` command line."""

import argparse
from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from brain import db


def _orch():
    from brain.orchestrator import Orchestrator

    return Orchestrator()


def _show(msg, out: dict) -> None:
    ext = out.get("extraction")
    facts = "" if ext is None or ext.type == "ignore" else \
        f" {ext.provider} ₹{ext.amount} due {ext.due_date}"
    flag = f"  [flagged: {'; '.join(out['problems'])}]" if out.get("problems") else ""
    print(f"{msg.received_at:%Y-%m-%d} {msg.kind:5} {msg.sender_key:22} -> {out['outcome']:12} "
          f"{out.get('handler', ''):10} {out.get('type', '')}{facts}{flag}")


def cmd_init(_args) -> None:
    db.init_db()
    print(f"database ready: {db.engine.url}")


def cmd_stats(_args) -> None:
    db.init_db()
    with db.Session() as s:
        for model in db.Base.__subclasses__():
            print(f"{model.__tablename__:16} {s.scalar(select(func.count()).select_from(model))}")


def cmd_ingest(args) -> None:
    """Ingest the synthetic fixtures (optionally up to a month), or specific .eml / .pdf files."""
    from brain.messages import from_eml
    from brain.sources.fixtures import load_fixtures
    from brain.sources.pdf import from_pdf

    db.init_db()
    if args.paths:
        msgs = [from_pdf(Path(p)) if p.endswith(".pdf") else from_eml(Path(p).read_bytes(), p) for p in args.paths]
    else:
        msgs = [m for m in load_fixtures() if not args.until or f"{m.received_at:%Y-%m}" <= args.until]
    orch = _orch()
    for m in msgs:
        _show(m, orch.ingest(m))


def cmd_imap(args) -> None:
    from brain.sources import imap

    db.init_db()
    orch = _orch()
    for m in imap.fetch(since=date.fromisoformat(args.since) if args.since else None, limit=args.limit):
        _show(m, orch.ingest(m))


def cmd_drain(_args) -> None:
    db.init_db()
    for out in _orch().drain():
        print(out["outcome"], out.get("source"), out.get("type", ""))


def cmd_ask(args) -> None:
    db.init_db()
    print(_orch().ask(" ".join(args.question)))


def cmd_compile(_args) -> None:
    from brain.compiler.generator import compile_pending
    from brain.llm import LLM

    db.init_db()
    with db.Session() as s:
        results = compile_pending(s, LLM())
        s.commit()
    for r in results:
        print(f"{r['ability']} v{r['version']}: {r['status']} (visible {r['visible']}, held-out {r['held_out']}, "
              f"held-out pass {100 * r['held_out_pass_rate']:.0f}%){'  ' + r['error'][:200] if r['error'] else ''}")
    if not results:
        print("nothing to compile")


def cmd_approve(args) -> None:
    from brain.compiler import registry

    db.init_db()
    with db.Session() as s:
        ab = registry.approve(s, args.name, actor="cli")
        s.commit()
    print(f"{ab.name} v{ab.version} -> shadow" if ab else f"no tested ability named {args.name!r}")


def cmd_abilities(_args) -> None:
    from brain.compiler import registry

    db.init_db()
    with db.Session() as s:
        for ab in registry.listing(s):
            print(f"{ab.name:40} v{ab.version} {ab.status:9} runs={ab.runs} failures={ab.failures} "
                  f"shadow_matches={ab.shadow_matches} {ab.last_error[:80]}")


def cmd_score(_args) -> None:
    from brain import score

    db.init_db()
    print(score.summary())


def cmd_fetch(args) -> None:
    """TinyFish Fetch (free): a web page through the same pipeline as email."""
    from brain.sources import tinyfish

    db.init_db()
    try:
        msg = tinyfish.fetch_message(args.url)
    except tinyfish.NotConfigured as e:
        return print(e)
    if args.expect_price is not None:
        seen = tinyfish.price_on_page(msg.body, args.expect_price)
        print(f"price {args.expect_price} {'found' if seen else 'NOT found'} on {args.url}")
    _show(msg, _orch().ingest(msg))


def cmd_portal(args) -> None:
    """TinyFish Agent: a goal on a portal page. Replays recorded runs unless TINYFISH_LIVE=1 (uses credits)."""
    from brain.sources import tinyfish

    db.init_db()
    try:
        out = tinyfish.portal(args.url, args.goal, schema=tinyfish.PRICE_SCHEMA if args.price else None,
                              record=args.record)
    except tinyfish.NotConfigured as e:
        return print(e)
    print(f"{'replayed' if out['replayed'] else 'live'} run -> {out['outcome']}: {out.get('result')}")
    if out.get("usage"):
        print(out["usage"])


def cmd_due(_args) -> None:
    from brain.telegram_bot import due_text

    db.init_db()
    print(due_text())


def cmd_say(args) -> None:
    """What the Telegram bot does with a free-text message: reply rules, planner, then chat."""
    from brain.planner import PlannerAgent
    from brain.telegram_bot import respond

    db.init_db()
    orch = _orch()
    print(respond(" ".join(args.text), orch, PlannerAgent(orch.llm)))


def cmd_serve_sms(args) -> None:
    import uvicorn

    db.init_db()
    uvicorn.run("brain.sources.sms_api:app", host=args.host, port=args.port)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="brain")
    sub = p.add_subparsers(required=True)
    sub.add_parser("init", help="create the SQLite schema").set_defaults(fn=cmd_init)
    sub.add_parser("stats", help="row counts per table").set_defaults(fn=cmd_stats)
    sp = sub.add_parser("ingest", help="ingest fixtures (default) or given .eml/.pdf files")
    sp.add_argument("paths", nargs="*")
    sp.add_argument("--until", help="last fixture month to ingest, YYYY-MM")
    sp.set_defaults(fn=cmd_ingest)
    sp = sub.add_parser("imap", help="ingest from IMAP (IMAP_HOST/IMAP_USER/IMAP_PASSWORD)")
    sp.add_argument("--since")
    sp.add_argument("--limit", type=int, default=100)
    sp.set_defaults(fn=cmd_imap)
    sub.add_parser("drain", help="retry queued sources").set_defaults(fn=cmd_drain)
    sp = sub.add_parser("ask", help="ask the chat agent (answers from state only)")
    sp.add_argument("question", nargs="+")
    sp.set_defaults(fn=cmd_ask)
    sub.add_parser("compile", help="detect repeated patterns and compile abilities").set_defaults(fn=cmd_compile)
    sp = sub.add_parser("approve", help="approve a tested ability for shadow mode")
    sp.add_argument("name")
    sp.set_defaults(fn=cmd_approve)
    sub.add_parser("abilities", help="list abilities with health stats").set_defaults(fn=cmd_abilities)
    sub.add_parser("score", help="privacy score and cost per message, per month").set_defaults(fn=cmd_score)
    sp = sub.add_parser("fetch", help="TinyFish Fetch a page into the pipeline")
    sp.add_argument("url")
    sp.add_argument("--expect-price", type=float, help="check that this price appears on the page")
    sp.set_defaults(fn=cmd_fetch)
    sp = sub.add_parser("portal", help="TinyFish Agent goal on a portal page (replay unless TINYFISH_LIVE=1)")
    sp.add_argument("url")
    sp.add_argument("goal")
    sp.add_argument("--price", action="store_true", help="use the price schema instead of the bill schema")
    sp.add_argument("--record", action="store_true", help="save the live response to tests/fixtures/tinyfish")
    sp.set_defaults(fn=cmd_portal)
    sub.add_parser("due", help="what is due in the next 7 days (no LLM)").set_defaults(fn=cmd_due)
    sp = sub.add_parser("say", help="send a chat message as if on Telegram (replies, planner, chat)")
    sp.add_argument("text", nargs="+")
    sp.set_defaults(fn=cmd_say)
    sp = sub.add_parser("serve-sms", help="run the POST /ingest/sms webhook")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8787)
    sp.set_defaults(fn=cmd_serve_sms)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

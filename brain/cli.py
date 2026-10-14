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
    sp = sub.add_parser("serve-sms", help="run the POST /ingest/sms webhook")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8787)
    sp.set_defaults(fn=cmd_serve_sms)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

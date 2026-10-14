"""Telegram channel (python-telegram-bot). Run: `make bot`.

The first chat to send /start becomes the owner (or set TELEGRAM_OWNER_ID); every other chat is ignored.
Commands: /start /due /score /abilities /approve <name> /audit /portal <url> [goal] /help.
Free text: rule-based replies first (1, done, snooze 1h, paid), then the Planner for track/remind requests,
then the Chat agent (answers from state only). PDFs sent to the bot go to the Document agent.
Background jobs in this process: reminders, a nightly compile + classifier retrain, and IMAP polling if set.
"""

import asyncio
import html
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import select

from brain import config, db, notify, replies, scheduler, score

OWNER_FILE = config.ROOT / "data" / "telegram_owner"
PLAN_HINT = re.compile(r"\b(remind|track|tablet|medicine|pill|daily|every (day|morning|night|week|month))\b", re.I)
HELP = """Sorted keeps your bills, renewals, subscriptions and medicines.
/due — what's due in the next 7 days (no AI)
/score — privacy score: how much runs as local code
/abilities — compiled abilities and their health
/approve <name> — move a tested ability into shadow mode
/audit — the last things I did
/portal <url> [goal] — read a bill page with TinyFish
Send a PDF bill to file it. Ask anything ("when is my car insurance due?").
Say "Track Mom's thyroid tablet, 1 every morning, 30 left" to start a medicine tracker.
Replies: 1 / done (dose taken), snooze 1h, paid [provider]."""


# ------------------------------------------------------------------ pure logic (tested without Telegram)
def due_text(days: int = 7) -> str:
    today = config.today()
    with db.Session() as s:
        obs = s.scalars(select(db.Obligation).where(db.Obligation.status != "paid",
                                                    db.Obligation.due_date.between(today, today + timedelta(days=days)))
                        .order_by(db.Obligation.due_date)).all()
        low = s.scalars(select(db.Medication).where(db.Medication.stock <= 5)).all()
    lines = [f"{o.due_date:%a %d %b} · {o.provider} {o.type}" + (f" ₹{float(o.amount):,.2f}" if o.amount else "")
             + (f"  ⚠️ {o.note}" if o.status == "flagged" else "") for o in obs]
    lines += [f"💊 {m.name} ({m.person}): only {m.stock} left" for m in low]
    return (f"Due in the next {days} days:\n" + "\n".join(lines)) if lines else f"Nothing due in the next {days} days."


def score_text() -> str:
    return "Privacy score (share of messages handled by local code):\n" + score.summary()


def abilities_text() -> str:
    from brain.compiler import registry

    with db.Session() as s:
        rows = [f"{a.name} v{a.version}: {a.status} (runs {a.runs}, failures {a.failures})"
                for a in registry.listing(s)]
    return "\n".join(rows) or "No abilities yet. They appear once a task repeats 3 times."


def approve_text(name: str) -> str:
    from brain.compiler import registry

    with db.Session() as s:
        ab = registry.approve(s, name, actor="telegram")
        s.commit()
    return f"Approved {ab.name} v{ab.version}: now in shadow mode." if ab else f"No tested ability called {name!r}."


def audit_text(n: int = 10) -> str:
    with db.Session() as s:
        rows = s.scalars(select(db.AuditLog).order_by(db.AuditLog.id.desc()).limit(n)).all()
    return "\n".join(f"{a.at:%d %b %H:%M} {a.actor}: {a.action} {a.detail}"[:200] for a in rows) or "Nothing yet."


def respond(text: str, orch, planner) -> str:
    if (reply := replies.handle(text)) is not None:
        return reply
    if PLAN_HINT.search(text) and (reply := planner.plan(text)):
        return reply
    return orch.ask(text)


def ingest_pdf(path, orch) -> str:
    from brain.sources.pdf import from_pdf

    out = orch.ingest(from_pdf(path, received_at=datetime.now()))
    ext = out.get("extraction")
    if ext is None or ext.type == "ignore":
        return f"Read {path.name}: nothing to file ({out['outcome']})."
    amount = f" ₹{ext.amount:,.2f}" if ext.amount else ""
    return f"Filed {path.name}: {ext.type} {ext.provider}{amount}, date {ext.due_date} ({out['outcome']})."


def nightly() -> None:
    """Background worker: compile repeated patterns and retrain the local classifier. Never auto-approves."""
    from brain.compiler.generator import compile_pending
    from brain.llm import LLM
    from brain.ml.train import labelled_examples, trace_examples, train

    with db.Session() as s:
        results = compile_pending(s, LLM())
        s.commit()
    train(labelled_examples() + trace_examples())
    tested = [r["ability"] for r in results if r["status"] == "tested"]
    if tested:
        notify.send_self("New abilities passed their tests: " + ", ".join(tested) + ". Approve with /approve <name>.")


def poll_imap() -> None:
    from brain.orchestrator import Orchestrator
    from brain.sources import imap

    orch = Orchestrator()
    for msg in imap.fetch(since=config.today() - timedelta(days=2)):
        orch.ingest(msg)


# ------------------------------------------------------------------ Telegram wiring
def owner() -> int | None:
    if v := config.env("TELEGRAM_OWNER_ID"):
        return int(v)
    return int(OWNER_FILE.read_text()) if OWNER_FILE.exists() else None


def main() -> None:
    from telegram import Update
    from telegram.constants import ParseMode
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    from brain.orchestrator import Orchestrator
    from brain.planner import PlannerAgent

    token = config.env("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (create a bot with @BotFather).")
    db.init_db()
    orch = Orchestrator()
    planner = PlannerAgent(orch.llm)

    def allowed(update: Update) -> bool:
        return update.effective_chat is not None and update.effective_chat.id == owner()

    async def reply(update: Update, fn, *args, pre: bool = False):
        text = await asyncio.to_thread(fn, *args)
        if pre:
            await update.message.reply_text(f"<pre>{html.escape(text)}</pre>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(text)

    async def start(update: Update, context):
        if owner() is None:
            OWNER_FILE.parent.mkdir(exist_ok=True)
            OWNER_FILE.write_text(str(update.effective_chat.id))
        if allowed(update):
            await update.message.reply_text(HELP)

    def command(fn, pre=False, with_args=False):
        async def handler(update: Update, context):
            if allowed(update):
                args = (" ".join(context.args),) if with_args else ()
                await reply(update, fn, *args, pre=pre)
        return handler

    def portal_text(args: str) -> str:
        from brain.sources import tinyfish

        url, _, goal = args.partition(" ")
        if not url:
            return "Usage: /portal <url> [goal]"
        try:
            out = tinyfish.portal(url, goal or "Find the amount due and the due date on this bill page.")
        except tinyfish.NotConfigured as e:
            return str(e)
        return f"{'Replayed' if out['replayed'] else 'Live'} TinyFish run: {out['outcome']} {out.get('result')}"

    async def text_message(update: Update, context):
        if allowed(update):
            await reply(update, respond, update.message.text, orch, planner)

    async def document(update: Update, context):
        if not allowed(update):
            return
        doc = update.message.document
        if doc.mime_type != "application/pdf":
            await update.message.reply_text("I can read PDFs for now (photo OCR is on the roadmap).")
            return
        dest = config.ROOT / "data" / "raw" / "uploads" / f"{datetime.now():%Y%m%d%H%M%S}_{doc.file_name}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        await (await doc.get_file()).download_to_drive(dest)
        await reply(update, ingest_pdf, dest, orch)

    async def photo(update: Update, context):
        if allowed(update):
            await update.message.reply_text("Photo OCR is on the roadmap. Please send the bill as a PDF.")

    async def post_init(app):
        loop = asyncio.get_running_loop()

        def sink(text: str) -> None:
            if (chat := owner()) is not None:
                asyncio.run_coroutine_threadsafe(app.bot.send_message(chat, text), loop)

        notify.SINKS.append(sink)
        scheduler.get(paused=False)
        scheduler.create_repeating("0 3 * * *", key="nightly", func_ref="brain.telegram_bot:nightly",
                                   name="nightly compile + retrain")
        if config.env("IMAP_USER"):
            scheduler.create_repeating("*/15 * * * *", key="imap", func_ref="brain.telegram_bot:poll_imap",
                                       name="poll IMAP inbox")

    app = Application.builder().token(token).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("due", command(due_text)))
    app.add_handler(CommandHandler("score", command(score_text, pre=True)))
    app.add_handler(CommandHandler("abilities", command(abilities_text)))
    app.add_handler(CommandHandler("approve", command(approve_text, with_args=True)))
    app.add_handler(CommandHandler("audit", command(audit_text)))
    app.add_handler(CommandHandler("portal", command(portal_text, with_args=True)))
    app.add_handler(MessageHandler(filters.Document.ALL, document))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # the request URL contains the bot token
    print("Sorted bot running. Send /start to your bot in Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()

"""Telegram front end for the simulation: the same engine as the dashboard. You are the person the data belongs
to; reminders, alerts, approvals and meeting requests arrive here as they happen on the simulated clock."""

import asyncio
import html

from brain import score
from brain.sim import how
from brain.telegram_bot import OWNER_FILE, abilities_text, due_text, owner

HELP = """<b>Sorted simulation</b>
You are Rohan Sharma. Six months of synthetic mail arrive as you move the clock.

<b>Clock</b>
/next  next message or reminder
/day  /week  /month  /end  jump ahead

<b>Look</b>
/sim  where the clock is
/due  what's due this week (no AI)
/score  privacy score per Sim month
/abilities  what has been compiled to code

<b>Change</b>
/generate &lt;description&gt;  add synthetic mail, e.g.
<i>/generate a supplier sending shipment requests between June and August</i>
/reset  start over

<b>Ask anything</b>
"any doctor appointments this month?"
"all my dues and updates between 1 June and 15 July"
Questions you repeat get compiled into code too. Replies: paid, snooze 1h, 1 (dose taken)."""
ICON = {"email": "📧", "sms": "💬", "pdf": "📄"}
TAG = {"compiled code": "⚡ code", "local ML": "🤖 local ML", "rule": "📏 rule", "LLM": "🧠 AI",
       "dropped before storage": "🗑 OTP, dropped"}


async def start(engine, token: str):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.constants import ParseMode
    from telegram.error import BadRequest
    from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

    app = Application.builder().token(token).build()
    loop = asyncio.get_running_loop()

    def allowed(update: Update) -> bool:
        return update.effective_chat is not None and update.effective_chat.id == owner()

    def summary(events: list[dict]) -> str:
        msgs = [e for e in events if e["kind"] == "message"]
        local = sum(e.get("label") in ("compiled code", "local ML", "rule", "dropped before storage") for e in msgs)
        now = engine.now()
        lines = [f"⏩ <b>{now:%a} {now.day} {now:%b %Y}, {now:%H:%M}</b> · Sim month {engine.month_of(now)}/6"]
        if msgs:
            lines.append(f"{len(msgs)} new message{'s' * (len(msgs) != 1)}: {local} by local code, "
                         f"{len(msgs) - local} by the AI\n")
        else:
            lines.append("No new messages.")
        for e in msgs[-8:]:
            kind, _, rest = e["title"].partition(" from ")
            sender, _, subject = rest.partition(": ")
            what = e.get("facts") or subject
            tag = TAG.get(e.get("label"), e.get("label"))
            lines.append(f"{ICON.get(kind, '•')} <b>{html.escape(sender)}</b> · {tag}\n      {html.escape(what[:90])}")
        if len(msgs) > 8:
            lines.append(f"…and {len(msgs) - 8} earlier")
        return "\n".join(lines)

    async def reply(update: Update, text: str, markup=None):
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup,
                                        disable_web_page_preview=True)

    async def run(fn, *args):
        return await asyncio.to_thread(fn, *args)

    async def start_cmd(update: Update, context):
        if owner() is None:
            OWNER_FILE.parent.mkdir(exist_ok=True)
            OWNER_FILE.write_text(str(update.effective_chat.id))
        if allowed(update):
            await reply(update, HELP)

    def stepper(to: str):
        async def handler(update: Update, context):
            if allowed(update):
                await reply(update, summary(await run(engine.step, to)))
        return handler

    async def sim_cmd(update: Update, context):
        if allowed(update):
            st = engine.status()
            now = engine.now()
            await reply(update, f"🕰 <b>{now:%a} {now.day} {now:%b %Y}, {now:%H:%M}</b>\nSim month {st['month']}/6 · "
                                f"{st['delivered']}/{st['total']} messages delivered")

    async def score_cmd(update: Update, context):
        if allowed(update):
            text = await run(score.summary)
            await update.message.reply_text(f"<pre>{html.escape(text)}</pre>", parse_mode=ParseMode.HTML)

    def plain(fn):
        async def handler(update: Update, context):
            if allowed(update):
                await update.message.reply_text(await run(fn))
        return handler

    async def reset_cmd(update: Update, context):
        if allowed(update):
            await run(engine.reset)
            await update.message.reply_text("Simulation reset. /next to let the first mail arrive.")

    async def generate_cmd(update: Update, context):
        if not allowed(update):
            return
        request = " ".join(context.args)
        if not request:
            await reply(update, "Describe the mail to add, e.g. <i>/generate a supplier sending shipment requests "
                                "between June and August</i>")
            return
        await reply(update, "✍️ Writing synthetic messages…")
        out = await run(engine.generate, request)
        if out.get("error"):
            await reply(update, html.escape(out["error"]))
            return
        await reply(update, f"➕ Added {len(out['ids'])} synthetic messages: <b>{html.escape(out['label'])}</b>\n"
                            f"{out['backfilled']} dated in the past arrived just now; {out['later']} arrive as the "
                            "clock moves. I re-check what I could learn as each one arrives.")

    async def text_message(update: Update, context):
        if allowed(update):
            out = await run(engine.ask, update.message.text)
            note = how(out.get("handler", ""), out.get("event", ""))
            await reply(update, f"{html.escape(out['answer'])}\n\n<i>{html.escape(note)}</i>", links(out))

    async def button(update: Update, context):
        q = update.callback_query
        if not allowed(update):
            return
        await q.answer()
        out = await run(engine.act, q.data)
        try:  # the buttons go away once answered
            await q.edit_message_text(f"{q.message.text}\n\n→ {out['text']}", reply_markup=links(out),
                                      disable_web_page_preview=True)
        except BadRequest:  # pressed twice: nothing changed
            pass
        if out.get("ics"):
            await context.bot.send_document(q.message.chat_id, out["ics"].encode(), filename="meeting.ics")

    def links(out: dict):
        row = [InlineKeyboardButton(label, url=out[k]) for k, label in
               (("meet", "🎥 Google Meet"), ("link", "📅 Add to Google Calendar")) if out.get(k)]
        return InlineKeyboardMarkup([row]) if row else None

    def to_owner(text: str, actions=None) -> None:
        if (chat := owner()) is None:
            return
        buttons = [InlineKeyboardButton(label, callback_data=a) for label, a in actions or []]
        rows = [buttons] if len(buttons) <= 2 else [[b] for b in buttons]  # long choices stack vertically
        markup = InlineKeyboardMarkup(rows) if buttons else None
        asyncio.run_coroutine_threadsafe(app.bot.send_message(chat, text, reply_markup=markup,
                                                              disable_web_page_preview=True), loop)

    from brain import notify

    notify.SINKS.append(to_owner)
    notify.ASK_SINKS.append(lambda text, acts: to_owner(text, acts))
    app.add_handler(CommandHandler(["start", "help"], start_cmd))
    for name in ("next", "day", "week", "month", "end"):
        app.add_handler(CommandHandler(name, stepper(name)))
    app.add_handler(CommandHandler("sim", sim_cmd))
    app.add_handler(CommandHandler("score", score_cmd))
    app.add_handler(CommandHandler("due", plain(due_text)))
    app.add_handler(CommandHandler("abilities", plain(abilities_text)))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("generate", generate_cmd))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    return app


async def stop(app) -> None:
    await app.updater.stop()
    await app.stop()
    await app.shutdown()

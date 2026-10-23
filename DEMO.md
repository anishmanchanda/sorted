# Running the Sorted demo

Everything here uses one **persistent synthetic dataset**: 81 fake messages (59 emails, 19 SMS, 3 PDFs) for a fake
household (Rohan Sharma, his mother Sunita, son Aarav), spread over six simulated months that end on
23 Oct 2026. It is committed in [`data/samples/`](data/samples) with its ground-truth labels in
[`data/eval/labels.jsonl`](data/eval/labels.jsonl), so every run sees exactly the same mail. No real person's data
is involved. (`make dataset` regenerates it so the timeline ends today; you rarely need that.)

What's in it, per simulated month: HDFC credit-card statements (email + SMS), BSES electricity, Airtel broadband
(email + SMS), LIC premiums, Netflix and Spotify receipts, Apollo Clinic appointments for Mom; plus price rises
(Spotify, Netflix, YouTube), car-insurance renewal reminders, four people asking for your time (a lawyer, a school
PTM, a CA, a contractor), a dentist appointment, promotions, OTP SMS, one phishing/prompt-injection email, and three
PDFs. In Sim month 6 HDFC changes its email layout.

## 0. Set up once

```bash
git clone https://github.com/anishmanchanda/sorted.git
```
```bash
cd sorted
```
```bash
make setup
```

API keys are optional. Without them, everything recorded replays from `data/llm_cache/`. You need a key
(`CEREBRAS_API_KEY` and/or `OPENAI_API_KEY` in `.env`) only for things nobody has recorded yet: chat questions you
type and messages you add yourself.

## 1. The 10-second version

```bash
make demo
```

Prints the whole six months and writes [`reports/demo_run.md`](reports/demo_run.md) and
[`reports/eval.md`](reports/eval.md). It auto-approves compiled abilities so you can watch the share of local code
grow.

## 2. The interactive version (dashboard + Telegram)

If your Telegram bot is running (`make bot`), stop it first: one bot token allows only one connection. Then:

```bash
make sim
```

Open **http://127.0.0.1:8000**. You are Rohan. The page has a simulated clock (top), the privacy score and the "From
AI to compiled code" cards (left), and a chat box, "Waiting for you" buttons and a live feed (right). The
**Synthetic inbox** tab lists every message and whether it has arrived yet.

A good walkthrough (about 5 minutes):

1. **Reset** (top right) to start at the beginning of Sim month 1. Tick **auto-approve (demo)** if you're presenting.
   Leave it off if you want to approve each ability yourself.
2. Press **To month end** three times (Sim months 1–3). The live feed tags every message **LLM**: nothing has been
   learned yet. OTPs show as *dropped before storage*, and the phishing email as *rule*. Reminders (⏰) fire on
   their dates with no AI.
3. At the end of Sim month 3 the compiler runs. Cards appear under **From AI to compiled code**: `hdfcbank_net_bill_due`,
   `bsesdelhi_com_bill_due`, `licindia_in_premium_due` and so on, each with its tests (shown + held-out). Without
   auto-approve, press **Approve** on each card, or in **Waiting for you**.
4. **To month end** for Sim month 4. The abilities run in *shadow* next to the LLM and become *active* when they
   agree.
5. **To month end** for Sim month 5. Those senders are now handled by **compiled code**: the privacy bar for Sim
   month 5 turns green, and each card's "% of this task's work offloaded to code" goes up.
6. When a **meeting request** arrives ("📅 Meeting request from Ravi Kumar (Acme Infra) · They proposed: Thu 29
   Oct, 11:00 AM"), press the proposed slot, or **Another time** and type e.g. "Friday 5pm" in the chat (a date
   parser reads it, no AI). You get reminders the day before and an hour before, a Google Meet link (a placeholder
   in Meet's format), a Google Calendar link and an `.ics`. Sorted then shows the reply it would send ("Thu 29 Oct
   doesn't suit me, but I can do Friday 30 October at 5:00 PM… Google Meet: …"). Press **Send** and it goes to the
   **Outbox** card; there is no mail server, so nothing actually leaves your machine. **Don't send** sends nothing.
7. **Run to today** for Sim month 6. HDFC's new email layout breaks `hdfcbank_net_bill_due@v1` (shown red,
   *degraded*). That message falls back to the LLM, and **v2** is compiled from the old and new layouts.
8. **Chat questions get compiled too** (needs an API key). Ask, one after another:
   - "Do I have any doctor appointments this month?"
   - "Any appointments coming up?"
   - "When is my next appointment?"

   The first three are answered by the LLM. Sorted then compiles `query_appointments` and asks for your approval.
   Approve it, ask a fourth ("any meetings this month?"; it runs in shadow), then a fifth ("do I have a doctor
   appointment next month?"). The answer is tagged **compiled code, 0 LLM calls**. If it ever misunderstands a
   phrasing, the LLM answers instead and the next version learns that phrasing.
9. **Ask about a date range** (needs an API key): "give me all my dues and updates between 1 August and 15
   September" lists bills due, appointments, requests and every update received in that window.
10. **Teach it something new** (needs an API key). In **Add synthetic data**, type "a business sending requests for
    new shipments sporadically between June and August" and press **Generate**. One AI call writes the emails.
    With no period they spread over the whole timeline, and ones dated before the clock arrive immediately. As
    they arrive the AI labels them as a new kind of message (`shipment_request`). After the third, Sorted says
    "🆕 New kind of message: Shipment requests… Learn this skill?". Press **Learn it**: the compiler writes and
    tests a parser (approve it), the next one runs in shadow, the one after is read by **compiled code**, and the
    skill reminds you the day before each requested dispatch date. Best done early (Reset, then generate), so
    there is timeline left for the messages to arrive. **Remove messages I added** (Synthetic inbox) undoes it.
11. Open the **Synthetic inbox** tab:
   - click any message to see the redacted text the AI and the compiled code actually see;
   - use **Add a synthetic message** (templates: meeting request, bill, doctor appointment), then press **Next
     event** to make it arrive.

The privacy panel shows, per Sim month: messages, how many were handled by local code, LLM calls, tokens, cost per
message (estimate) and the privacy score. A tile counts chat questions answered by code.

## 3. Doing the same from Telegram

With `make sim` running and `TELEGRAM_BOT_TOKEN` in `.env`, open your bot in Telegram (ours is **@sorted_admin_bot**)
and send `/start`. The first chat that does this becomes the owner; every other chat is ignored.

| Send | What happens |
|---|---|
| `/next` | The next message or reminder arrives |
| `/day`, `/week`, `/month`, `/end` | Move the clock 1 day, 1 week, to the end of this Sim month, or to the end of the dataset |
| `/sim` | Where the clock is |
| `/score` | Privacy score per Sim month |
| `/due` | What's due in the next 7 (simulated) days, no AI |
| `/abilities` | What has been compiled to code |
| `/generate <description>` | Add AI-written synthetic mail, e.g. `/generate a supplier sending shipment requests between June and August` |
| `/reset` | Start over |
| "all my dues and updates between 1 Aug and 15 Sep" | A digest of that window: dues, appointments, requests, updates received |
| Any question, e.g. "do I have any doctor appointments this month?" | An answer from your simulated inbox, tagged 🧠 LLM or ⚡ compiled code, 0 LLM calls |
| `paid` / `paid HDFC` | Marks the last-reminded (or named) bill as paid, no AI |
| `snooze 1h` | Re-sends the last reminder an hour later (simulated time) |
| "Track Mom's thyroid tablet, 1 every morning, 30 left" | Starts a medicine tracker. Each 8 AM it asks; reply `1` when taken, and it alerts you when 5 are left |

Reminders, price-rise alerts, approval requests ("🧪 New ability … passed its tests. Approve?"), new-skill proposals,
meeting requests (with *Another time*: just reply with the time) and reply drafts arrive in the chat on their own as the clock moves, with buttons where you need to decide something. The dashboard
and Telegram drive the same simulation, so you can use both at once.

## 4. Real use (not the simulation)

`make bot` runs the bot on your own data instead (`data/brain.db`). Reminders fire at real times, it compiles
nightly, and you approve with `/approve <name>`. Send it PDFs, ask questions, or set up IMAP in `.env`. `/score`
there shows only your real usage; `/score demo` shows the simulation.

## Resetting and regenerating

- **Dashboard Reset** or Telegram `/reset`: replays the same dataset from Sim month 1.
- **`make demo`:** also resets the interactive simulation, because they share `data/demo.db`.
- **`make dataset`:** regenerates the synthetic dataset so it ends today. The recorded LLM answers still replay,
  because their dates are shifted to match. Run `make demo` afterwards to refresh the reports.

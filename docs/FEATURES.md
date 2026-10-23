# Sorted: what is built

Everything on this page is in the repo and working. Each feature says where the code lives and how to see it.
Figures come from [`reports/demo_run.md`](../reports/demo_run.md) and [`reports/eval.md`](../reports/eval.md), a
run over six simulated months of **synthetic** mail (81 messages; no real person's data). For how this maps onto
what we submitted to IIIT Delhi, see [`PROPOSAL_VS_BUILT.md`](PROPOSAL_VS_BUILT.md).

**Contents**
1. [The core idea: AI as a compiler](#1-the-core-idea-ai-as-a-compiler)
2. [Getting data in](#2-getting-data-in)
3. [Understanding messages](#3-understanding-messages)
4. [Memory: typed state](#4-memory-typed-state)
5. [The ability compiler](#5-the-ability-compiler)
6. [Learning new kinds of work](#6-learning-new-kinds-of-work)
7. [Acting with no AI: scheduler, rules, reminders, medicines](#7-acting-with-no-ai)
8. [Meeting requests](#8-meeting-requests)
9. [Asking questions](#9-asking-questions)
10. [Channels: Telegram and MCP](#10-channels-telegram-and-mcp)
11. [The web: TinyFish](#11-the-web-tinyfish)
12. [Privacy and safety](#12-privacy-and-safety)
13. [The harness: budgets, routing, replay, tracing](#13-the-harness)
14. [Measuring it: privacy score, evals, tests](#14-measuring-it)
15. [Showing it: simulation, dashboard, autopilot](#15-showing-it)

---

## 1. The core idea: AI as a compiler

Every message goes through one pipeline ([`brain/orchestrator.py`](../brain/orchestrator.py)):

```
OTP filter → store source (redacted) → injection guard → active compiled ability? → local classifier
→ LLM agent (only if nothing local handled it) → validate → typed state → rules → trace
```

- **The LLM is used to learn or repair a task, not to run it.**
- **Every LLM solve is saved as a trace.** When the same kind of task repeats (3 times from one sender), a
  compiler agent writes deterministic Python for it.
- **The code is tested before it runs:** on past cases and held-out cases, then approved by you. It runs in shadow
  next to the LLM, and only then takes over (**active**: 0 LLM calls).
- **When it breaks,** the message falls back to the LLM and version 2 is compiled.

**Result (synthetic data):** messages handled by local code per Sim month went **0% → 0% → 7% → 0% → 62% → 47%**.
Sim month 4 is the shadow month, where the AI's answer is still used. In Sim month 6, HDFC's layout change and new
one-off senders go back to the AI.

## 2. Getting data in

| Source | How | Where |
|---|---|---|
| Email files | `brain ingest <.eml …>`; the synthetic inbox by default | [`brain/sources/fixtures.py`](../brain/sources/fixtures.py), [`brain/messages.py`](../brain/messages.py) |
| A real inbox (Gmail with an app password, Outlook, iCloud…) | Read-only IMAP: `brain imap --since 2026-01-01 --limit 100` | [`brain/sources/imap.py`](../brain/sources/imap.py) |
| PDFs | Text PDFs via pdfplumber (bills, policies, certificates); `brain ingest file.pdf` or sent to the bot | [`brain/sources/pdf.py`](../brain/sources/pdf.py) |
| SMS | `POST /ingest/sms` webhook with a per-user bearer token, for an Android forwarder or an iPhone Shortcut (`brain serve-sms`) | [`brain/sources/sms_api.py`](../brain/sources/sms_api.py) |
| Web pages and portals | TinyFish Fetch and Agent (see §11) | [`brain/sources/tinyfish.py`](../brain/sources/tinyfish.py) |
| Chat | Telegram messages and PDF uploads | [`brain/telegram_bot.py`](../brain/telegram_bot.py) |

Duplicate messages (same body hash) are skipped.

## 3. Understanding messages

- **Specialist agents**, each a plain class with an explicit `TOOLS` list ([`brain/agents.py`](../brain/agents.py),
  [`brain/planner.py`](../brain/planner.py)):
  - **Inbox** (email), **Document** (PDF, SMS, web pages), **Chat** (answers from state only), **Planner**
    (turns "remind me…/track…" into jobs).
  - None of them has a tool to send to others, pay, forward or delete. A test enforces this.
- **Typed extraction** ([`brain/validate.py`](../brain/validate.py)). Message types:
  - `bill_due`, `premium_due`, `insurance_renewal`, `subscription_receipt`, `subscription_price_change`;
  - `meeting`, `meeting_request`, `document_expiry`;
  - `other` (a new kind of message, with a category the AI names), and `ignore`.
- **Validation** on every result, from the LLM or from compiled code: amount > 0 where needed, due date inside a
  sane window, provider present, category well-formed. A result that fails is flagged, never silently stored.
- **Local ML classifier**, two layers ([`brain/ml/`](../brain/ml)):
  - exact sender rules, plus TF-IDF + logistic regression, retrained on the LLM's own labels;
  - a confident `ignore` (promotions, newsletters) never reaches the LLM.
  - Held-out accuracy **88.7%**; **82.6%** of predictions are confident, and those are **100%** correct.
- **Extraction accuracy** on 77 labelled non-OTP synthetic messages: **100%** type, provider and due date; amount
  **98.6%** (LLM 53/54, compiled code 15/15).

## 4. Memory: typed state

SQLite through SQLAlchemy ([`brain/db.py`](../brain/db.py), [`brain/state.py`](../brain/state.py)):

- **Typed records:** obligations (bills, premiums, renewals, subscriptions, meetings, new categories),
  subscriptions, documents, medications.
- **Provenance:** every fact links to its **source record** (redacted text and a hash), so you can trace it back.
- **Conflicts:** two different due dates or amounts for the same thing are **flagged**, never overwritten.
  Duplicates (email + SMS of the same bill) are linked.
- **Traces:** every LLM call and every compiled run. **Audit log:** every action, reminder, approval and reply.
- Two databases: `data/brain.db` for real use, `data/demo.db` for the simulation. The simulation can never touch
  real data.

## 5. The ability compiler

[`brain/compiler/`](../brain/compiler): `detector` → `generator` → `static_check` → `sandbox` → `registry`.

| Stage | What happens |
|---|---|
| Candidate | The detector groups accepted LLM traces by (source kind, sender, type); 3 or more make a candidate |
| Generated | The compiler agent (strong model) writes `extract(text) -> dict` from 70% of the cases; 30% are **held out** |
| Static check | AST allowlist: imports only `re`, `datetime`, `decimal`, `html`, `json`, `dateutil`, `typing`; no `open`/`eval`/`exec`/dunders/`os`/`socket` |
| Tested | Runs in a **separate process** with an empty environment, sockets blocked, resource limits and a timeout. Must pass every visible case and ≥ 98% of held-out cases. One retry with the failures fed back |
| Approved | You approve, with a Telegram/dashboard button or `brain approve` |
| Shadow | Runs next to the LLM; the LLM's answer is still used until they agree |
| Active | Handles that sender alone: **0 LLM calls** |
| Degraded → v2 | Fails validation (e.g. a missing amount) → that message falls back to the LLM → v2 is compiled from old and new layouts |

- **Results:** 11 parser versions compiled from the synthetic inbox, including `hdfcbank_net_bill_due` v2 after
  HDFC's Sim-month-6 layout change.
- **Exported for review:** every ability goes to [`abilities/`](../abilities) with its cases and a standalone
  pytest file. `uv run pytest abilities` runs the **37** tests the compiler generated for its own code.

## 6. Learning new kinds of work

### Compiled chat questions ([`brain/query.py`](../brain/query.py))
- **Typed query, fixed answer code.** The LLM only turns a question into `{intent, period, provider, start,
  end}`. Fixed read-only code runs the query and fills a template answer.
- **Repeated question types get compiled.** Ask the same kind of question 3 times and the compiler writes a
  recogniser. It is tested on your past questions and on other questions it must not claim.
- **Same path as parsers:** approve → shadow → active. Answers are then tagged **"compiled code · 0 AI calls"**.
- **Self-repair:** phrasings it misses go to the LLM, and repeated misses compile v2.

### New kinds of messages become new skills ([`brain/skills.py`](../brain/skills.py))
- **The AI names new kinds of message.** When no known type fits, it labels the message `other` with a category
  it invents (e.g. `shipment_request`).
- **Sorted proposes a skill on its own.** Sorted **re-assesses after every message**. When a category repeats 3
  times, it asks *"🆕 New kind of message: Shipment requests… Learn this skill?"*
- **The plan is limited to safe actions.** One LLM call plans the skill and picks one action from a fixed list:
  remind you before each one's date, message you when one arrives, or just track them. None contacts anyone.
- **Code only after you agree.** If you agree, the compiler writes and tests a parser for them, and every later
  one triggers the action with no AI.

### Synthetic data on demand
- **Describe it, and the AI writes it.** Describe new data ("a business sending requests for new shipments
  sporadically between June and August") on the dashboard or with `/generate`, and one LLM call writes realistic,
  templated messages.
- **Past-dated messages backfill at once;** the rest arrive as the simulated clock moves, so you can watch Sorted
  discover and learn them.

## 7. Acting with no AI

- **Scheduler** ([`brain/scheduler.py`](../brain/scheduler.py)):
  - APScheduler with a SQLAlchemy job store, so jobs survive restarts;
  - one-time, repeating (cron) and relative jobs ("3 days before due");
  - quiet hours (`BRAIN_QUIET_HOURS`, default 22–07); reminders due within 15 minutes of each other are merged
    into one message.
  - The **AI decides what to schedule; plain code decides when.** A reminder firing costs no tokens. 32 reminders
    fired on time in the simulated run.
- **Reply handlers** ([`brain/replies.py`](../brain/replies.py)): `paid` / `paid HDFC` marks a bill paid,
  `snooze 1h` re-sends later, and `1` / `done` logs a medicine dose, all with no LLM.
- **Rules as data** ([`brain/rules/*.yaml`](../brain/rules)), with a fixed action set and declared permissions:
  - `subscription_price_increase`: *"Spotify is raising your price from ₹119 to ₹139 on 28 Jul. Reply KEEP or
    CANCEL-HELP."* (3 price-rise alerts fired: Spotify, Netflix, YouTube);
  - `subscription_price_update`;
  - `medicine_refill` (stock ≤ 5).
- **Medicine tracker:** "Track Mom's thyroid tablet, 1 every morning, 30 left" → one LLM call creates the
  medication and a daily 8 AM job. Replying `1` logs the dose and lowers the stock, and the refill alert fires at
  5. Nothing after the first message uses the AI.

## 8. Meeting requests

[`brain/meetings.py`](../brain/meetings.py), [`brain/actions.py`](../brain/actions.py).

1. **Sorted asks.** An email asking for your time arrives, and Sorted asks: *"📅 Meeting request from Ravi Kumar
   (Acme Infra) · About: kitchen renovation site visit · They proposed: Thu 29 Oct, 11:00 AM. Do you want to
   meet?"*
2. **You pick a time.** Three buttons: the proposed slot, **Another time**, or **Decline**. With Another time you
   type e.g. "Friday 5pm"; a date parser reads it, with no AI.
3. **It books.** Reminders go in for the day before and an hour before, with a **Google Meet** link, a prefilled
   **Google Calendar** link and an `.ics` file.
4. **It drafts a reply** to the person, from a template (*"Thu 29 Oct doesn't suit me, but I can do Friday 30
   October at 5:00 PM… Google Meet: …"*). The reply is sent **only if you press Send**.
5. **Limits:**
   - "Sent" means it goes to the outbox; no mail server is connected.
   - The Meet link is a placeholder in Meet's format until a Google Calendar API connection creates real ones.

## 9. Asking questions

From Telegram, the dashboard, the CLI (`brain ask`) or MCP:

| Question type | Example |
|---|---|
| What's due | "What do I need to pay in the next two weeks?" (gives the total and each bill) |
| Appointments | "Do I have any doctor appointments this month?" |
| **Date ranges / digest** | "Give me all my dues and updates between 1 August and 15 September" (dues, appointments, requests and every update received in that window) |
| Subscriptions, documents, medicines, price changes | "What subscriptions do I pay for?" |
| Anything else | Answered by the Chat agent from a compact pack of typed state, never from raw email |

`/due` answers "what's due this week" with **no AI** at all.

## 10. Channels: Telegram and MCP

### Telegram ([`brain/telegram_bot.py`](../brain/telegram_bot.py), tested live)
- **Commands:** `/due`, `/score` (real use) and `/score demo` (the simulation), `/abilities`, `/approve <name>`.
- **Other input:** free-text questions, PDF uploads, reply handlers, and medicine tracking.
- **Owner only:** the first chat to send `/start` becomes the owner; every other chat is ignored.

### Brain MCP server ([`brain/mcp_server.py`](../brain/mcp_server.py), tested end to end with the official MCP client)
- **Tools:** `get_upcoming`, `search_obligations`, `get_obligation`, `mark_paid`, `create_reminder`,
  `list_abilities`, `run_ability` (approved abilities only, sandboxed), `get_privacy_score`.
- **Resources:** `sorted://profile`, `sorted://digest`.
- **Prompts:** `weekly_review`, `what_do_i_owe_this_month`.
- **Transports:** stdio (`make mcp`) for Claude Desktop and Cursor, or Streamable HTTP (`make mcp-http`) with a
  bearer token and a read / read-write scope. Write calls are audit-logged.

## 11. The web: TinyFish

[`brain/sources/tinyfish.py`](../brain/sources/tinyfish.py):

- **Fetch** (`brain fetch <url>`) reads a page into the same pipeline as email.
- **Search** finds pages.
- **Agent** (`brain portal <url> "<goal>"`) runs a natural-language goal on a real site and stores the result as a
  `portal` trace, so the task can graduate like any other.
  - **Recorded run:** one real Agent run read Netflix's plan page (US pricing, because TinyFish has no India exit).
  - **Offline replay:** it replays from [`tests/fixtures/tinyfish/`](../tests/fixtures/tinyfish) unless
    `TINYFISH_LIVE=1`, so demos and tests never spend credits.

## 12. Privacy and safety

- **Redaction before every LLM call,** inside the LLM wrapper, so no caller can skip it. It masks emails, card,
  phone and account/policy numbers ([`brain/redact.py`](../brain/redact.py)).
- **OTP SMS are dropped before storage.** Only the fact that one was dropped is logged.
- **Prompt-injection guard:** obvious injection text never reaches the LLM, and message text is always passed as
  data. Tested on a phishing email in the dataset.
- **No outbound actions by any agent:**
  - nothing can pay, forward or delete;
  - the only message to anyone else is the meeting reply, a template that goes out only on your button press.
- **Generated code is contained:** AST allowlist, a separate sandboxed process, held-out tests, human approval,
  and shadow mode before it is trusted.
- **Approvals by button** for every new ability, skill, meeting and reply. **Audit log** of everything.
- **Shrinking exposure:** once a sender's ability is active, its messages are never sent to an LLM again.

## 13. The harness

[`brain/llm.py`](../brain/llm.py):

- **Model routing:** `small` (Cerebras gpt-oss-120b) for extraction and chat, `strong` (OpenAI gpt-5.4) for the
  compiler.
- **JSON mode** with Pydantic validation and one repair retry.
- **Token budgets** per run and per day. When a budget runs out, the message is **queued**, not lost, and
  `brain drain` retries it.
- **Cost accounting:** every call's tokens and estimated cost go into the traces table.
- **Record/replay cache** ([`data/llm_cache/`](../data/llm_cache)), so the whole demo replays offline with **no
  API key**. Replayed dates shift so the timeline always ends today.

## 14. Measuring it

- **Privacy score:** the share of messages handled by local code (compiled abilities, local ML, rules), per month,
  with cost per message. Available from `brain score`, `/score`, MCP `get_privacy_score` and the dashboard.
- **Eval set:** 81 labelled synthetic messages ([`data/eval/labels.jsonl`](../data/eval/labels.jsonl)) covering
  bills, premiums, renewals, subscriptions, price changes, appointments, meeting requests, documents, promotions,
  OTPs and a phishing email. `make eval` scores extraction per handler and the classifier.
- **Tests:** **60 offline tests** (`make test`; the LLM, TinyFish and HTTP are mocked), plus the 37 generated
  ability tests.

## 15. Showing it

| Command | What you get |
|---|---|
| `make demo` | Six simulated months in seconds; prints them and writes `reports/demo_run.md` and `reports/eval.md`. Replays offline |
| `make sim` | A dashboard at http://127.0.0.1:8000 plus the same simulation in Telegram, on a clock you control |
| Telegram `/run` (or **▶ Run full demo**) | The whole demo on autopilot, one event every few seconds, saying yes to every approval, skill, meeting and reply |
| `/fast`, `/normal`, `/slow`, `/stop` | Change the pace mid-run, or pause |
| `/next`, `/day`, `/week`, `/month`, `/end` | Step by hand; each month's opening and recap are posted too |

**The dashboard shows:**
- **Month by month:** one card per Sim month that follows the clock, with the split of messages between code and
  the AI and plain-language highlights, e.g. *"⚙️ Learned to read HDFC Bank bill emails: code written and
  tested"*, *"✅ Appointment questions now handled by code"*, *"💥 HDFC Bank bill emails changed layout: the code
  broke and the AI took over again"*, *"🆕 Noticed a new kind of message and learned a skill for it"*.
- **Skills learned so far,** with the month each was written and the month it took over.
- **Privacy score and cost tiles.**
- **"From AI to compiled code":** every ability's path, with the code the AI wrote and its tests.
- **The synthetic inbox,** where you can add or generate messages.
- **A live feed and an outbox.**

See [`../DEMO.md`](../DEMO.md) for the walkthrough.

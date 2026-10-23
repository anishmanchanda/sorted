# What we proposed vs. what we built

What Team Not Found (Anish Manchanda, Aryan Thakur, Keshav Goel) submitted to **HackIIITD 2026 (IIIT Delhi), Round
1**, checked item by item against the code in this repo. There were two documents:

- **The deck:** *Personal Admin Brain: AI as a compiler, not an interpreter* (9 slides,
  `Personal_Admin_Brain_HackIIITD.pdf`).
- **The design doc:** *Personal Admin Brain: Project Design Draft* ([`design.pdf`](design.pdf), 27 pages, a 12-week
  plan).

The project is now called **Sorted**. Every "measured" number below comes from [`reports/`](../reports): six
simulated months of **synthetic** mail. No real inbox has been measured yet.

| Mark | Meaning |
|---|---|
| ✅ | Built and working as proposed |
| 🟡 | Built, but differently or partly (the difference is stated) |
| ⏳ | Not built yet |
| ➕ | Built, and not in the proposal |

---

## Part 1: The deck, slide by slide

### Slide 1: "AI as a compiler, not an interpreter"
> "learns your bills, renewals, medicines and documents with AI, then compiles what it learned into tested local
> code, so it gets cheaper, faster and more private every month"

- ✅ **The core loop works end to end.** The LLM learns a sender's messages; after 3 examples, a compiler agent
  writes Python and tests it on held-out cases. After your approval and a shadow period, the code handles that
  sender with **0 LLM calls**.
- ✅ **"More private every month" is measured,** as messages handled by local code per Sim month: **0% → 0% → 7% →
  0% → 62% → 47%**.
- ✅ **It covers** bills, renewals, premiums and subscriptions, plus medicines (the tracker) and documents (expiry
  dates from PDFs and email).

### Slide 2: Problem statement
- ✅ **The categories on the slide are handled:**
  - **bills:** credit card, electricity, broadband, mobile SMS;
  - **insurance and LIC:** premium due, renewal reminders, policy PDFs;
  - **subscriptions:** receipts, *silent renewals and quiet price hikes*, which trigger price-rise alerts;
  - **medicines:** doses and refills;
  - **documents:** a PUC certificate PDF gives an expiry date.
- ✅ **The synthetic household is Indian:** HDFC, BSES Rajdhani, Airtel, LIC, ICICI Lombard, Apollo Clinic, a
  PUC certificate, ₹ amounts and Indian number formats.
- 🟡 **FASTag, Parivahan and RC renewal** are not in the dataset. Those live on portals, which is the TinyFish
  graduation still to be built (slide 6).

### Slide 3: Proposed solution

| Promised | Status |
|---|---|
| Graduation: LLM handled → Candidate (3+ times) → Generated → Tested → Shadow (you approve) → Active (zero AI) | ✅ Exactly this lifecycle ([`brain/compiler/`](../brain/compiler)) |
| "If an ability breaks (new bill layout, failed validation…) falls back to the LLM, collects new traces and compiles version 2" | ✅ Shown live: HDFC changes its email layout in Sim month 6 → `hdfcbank_net_bill_due` v1 fails validation → that message goes back to the LLM → v2 is compiled from both layouts |
| **Collect:** Gmail | 🟡 Read-only **IMAP** (works with Gmail through an app password), not the Gmail MCP server |
| **Collect:** PDFs and Drive | 🟡 PDFs ✅ (pdfplumber); Google Drive ⏳ |
| **Collect:** bank SMS via the Android app or iPhone Shortcuts | 🟡 The **SMS webhook** (`POST /ingest/sms`, per-user tokens, OTP filter) is built; the Android app and Shortcut themselves ⏳ |
| **Collect:** biller and government portals via TinyFish | 🟡 TinyFish Fetch, Search and Agent adapters are built, with one real Agent run recorded; scheduled portal checks ⏳ |
| **Collect:** photos and PDFs forwarded to the bot | 🟡 PDFs ✅; photos need OCR ⏳ |
| **Remember:** typed records; every fact linked to its source; conflicts flagged, never overwritten | ✅ All three ([`brain/state.py`](../brain/state.py)) |
| **Act:** reminders on Telegram | ✅ (Discord ⏳) |
| **Act:** events in Google Calendar | 🟡 Meetings get a prefilled **Google Calendar link** and an `.ics` file ➕; writing to the calendar through the Calendar API ⏳ |
| **Act:** medicine and refill tracking | ✅ |
| **Act:** serves Claude, ChatGPT, Cursor over MCP | ✅ Brain MCP server (stdio + Streamable HTTP), tested with the official MCP client |

### Slide 4: Target users
- ✅ **The family admin:** one chat with everything due (`/due`, "what do I owe this month?"), reminders that fire
  on time with no AI, and a digest ("all my dues and updates between X and Y") ➕.
- ✅ **Parents and elders:** fixed reminders, e.g. "Time for Mom's thyroid tablet. Reply 1 when taken"; replying
  `1` logs the dose, and a refill alert follows. No app to learn.
- ✅ **Power users:** self-hosted, open source, and an MCP server so Claude or Cursor get reliable facts.
- ✅ **Telegram-first onboarding:** nothing to install; the first chat to `/start` becomes the owner.

### Slide 5: Technical architecture and stack

| Layer / stack item (deck) | Status |
|---|---|
| Channel gateway + ingestion queue | 🟡 One internal `Message` format, with adapters for email/IMAP/PDF/SMS/web. Queueing happens when the LLM budget runs out (`queued` → `brain drain`); there is no separate queue service |
| Orchestrator + harness: checks the ability registry first · budgets · checkpoints · approval gates · tracing | ✅ Registry first, budgets, approval gates, traces table. 🟡 Checkpoints = queued sources resume; no step-level task checkpoints |
| Ability runtime: tested local code, no AI | ✅ |
| Specialist agents: Inbox · Document · Planner · Auditor · Chat | 🟡 Inbox, Document, Planner, Chat ✅; **Auditor ⏳**. The Compiler agent ✅ |
| Scheduler: plain timers | ✅ APScheduler with a SQL job store, quiet hours, merging |
| Ability registry: versioned + health; Ability compiler: traces → code + tests → shadow → active | ✅ Runs, failures, shadow matches and last error per version |
| State store: typed SQLite, encrypted | 🟡 Typed SQLite ✅; encryption (SQLCipher) ⏳ |
| Brain MCP server: state + abilities as tools | ✅ |
| Core: Python 3.12, FastAPI, asyncio | ✅ |
| LLM: Claude API via a router; Ollama local | 🟡 A two-route router (small = Cerebras gpt-oss-120b, strong = OpenAI gpt-5.4) via one wrapper; Ollama ⏳ |
| Web: TinyFish Agent, Fetch, Search, Browser | 🟡 Agent, Fetch, Search ✅; Browser-API replay of compiled scripts ⏳ |
| State: SQLite + SQLCipher, sqlite-vec | 🟡 SQLite ✅; SQLCipher, sqlite-vec ⏳ |
| Jobs: APScheduler, SQL job store | ✅ |
| Sandbox: Docker, no network | 🟡 A **separate subprocess** with an empty environment, sockets blocked, rlimits and a timeout, plus an AST allowlist; Docker `--network none` ⏳ |
| MCP: FastMCP; Gmail, Calendar, Drive clients | 🟡 Our own MCP server ✅ (official MCP Python SDK); the Gmail/Calendar/Drive **client** side ⏳ |
| Chat: python-telegram-bot, discord.py | 🟡 python-telegram-bot ✅; Discord ⏳ |
| Docs: pdfplumber, PyMuPDF, Tesseract | 🟡 pdfplumber ✅; PyMuPDF, Tesseract ⏳ |
| SMS: Kotlin + WorkManager; Shortcuts | ⏳ (the server-side webhook they post to is ✅) |
| Ops: Langfuse, Docker Compose | ⏳ (the traces table records every call, its cost and result; `make` targets run everything) |

### Slide 6: How we integrate the TinyFish API

| TinyFish API | Role in the deck | Status |
|---|---|---|
| **Agent API** (LEARN) | Natural-language goals on real sites | ✅ `brain portal <url> "<goal>"`. One real run is recorded (Netflix plan page) and stored as a `portal` trace; it replays offline unless `TINYFISH_LIVE=1`. Streaming to chat ⏳ |
| **Fetch API** (READ) | Render a URL, feed parsers | ✅ `brain fetch <url>` puts the page through the same pipeline as email |
| **Search API** (FIND) | Locate the official portal, cheaper plans | ✅ Adapter built and tested live |
| **Browser API** (REPLAY) | Replay the compiled script | ⏳ |

> "The compiler, applied to the web: Agent run → Compile → Replay → Self-heal"

- 🟡 **Built:** the *Agent run* step, and the trace it produces.
- ⏳ **Not built:** compiling a portal flow into a Playwright script and replaying it on a schedule. This is the
  next milestone. The same compile → shadow → self-heal machinery already works for email and SMS.
- ✅ **The safety line holds:** "the Brain never sends payments or submits forms on its own".

### Slide 7: Use case, "a bill that never reaches email"

| Stage | Proposed (portal bill) | What runs today |
|---|---|---|
| Month 1: Learn | The TinyFish Agent reads the portal, saves the obligation and a reminder | 🟡 The same stage runs for **email/SMS bills**: LLM extraction, obligation, reminder 3 days before. The portal version is the recorded Agent run |
| Months 2–3: Compile | Flow repeats → candidate → compiler writes script + parser → shadow | ✅ for email/SMS: 8 parsers compiled and tested at the end of Sim month 3, shadow in Sim month 4 |
| Month 4+: Run AI-free | Scheduler triggers the script; parser extracts; reminder with zero LLM calls | ✅ for email/SMS: Sim month 5 is **62%** local code; reminders fire from templates |
| Redesign: Self-heal | Validation fails → fall back → v2 compiled automatically | ✅ The HDFC layout change in Sim month 6 → v2 |

> "Same pattern everywhere: … LIC premium due dates, bank statement emails, Netflix price-hike emails and
> medicine schedules"

- ✅ Each of these is in the synthetic data and runs through the pipeline: LIC premium due, HDFC statement emails,
  Netflix/Spotify/YouTube price-hike emails, and the medicine schedule.
- ⏳ FASTag and PUC *portals* are not covered yet; PUC is covered from a certificate PDF.

### Slide 8: Scalability and feasibility

**The design targets, against what we measured.** The deck said "Design targets, to be measured … To be reported
monthly as the Brain's privacy score." It is now measured, on synthetic data:

| Target (share of tasks as local code) | Measured (Sim month) |
|---|---|
| Week 1: under 10% | Sim month 1: **0%** |
| Month 1: 30% | Sim month 2: **0%** |
| Month 3: 60% | Sim month 3: **7%** · Sim month 4: **0%** (shadow month) |
| Month 6: 80% | Sim month 5: **62%** · Sim month 6: **47%** |

**Why the curve is slower than the targets.**
- **Monthly senders take time.** Most senders write once a month, so a sender needs three months to reach 3
  examples, then a shadow month before its code is trusted.
- **Sim month 6 mixes in new work.** It has the HDFC layout change (that message goes back to the AI on purpose),
  new meeting requests and one-off senders, so its share drops.
- **Real inboxes may differ.** With more frequent senders (SMS alerts, weekly mail) the curve would rise faster,
  but that is not measured yet.

**Other claims on the slide:**

| Claim | Status |
|---|---|
| "Cost per user falls over time" | 🟡 Cost per message (USD, estimated): 0.00063 → 0.00060 → **0.00556** (the compiler runs) → 0.00249 → 0.00252 → 0.00115. It falls after the compile month; it is not monotonic |
| "Learned abilities are code… can serve every user of that bank (code is shared, never data)" | 🟡 Abilities are exported as standalone code + tests in [`abilities/`](../abilities); sharing between users ⏳ |
| "Wrong money or medicine facts: output validation, shadow mode, source link on every fact" | ✅ All three |
| "Prompt injection: content is data, no send or pay permissions" | ✅ An injection guard, plus agents with no send/pay tools (enforced by a test); a phishing email in the dataset never reaches the LLM |
| "Platform rules: Telegram first; WhatsApp only for fixed reminders; SMS app sideloaded" | ✅ Telegram first; WhatsApp and the SMS app ⏳ |
| Stateless workers behind a queue; Postgres for hosted mode | ⏳ |

### Slide 9: MVP, the 24-hour build plan

**The six MVP components:**

| # | Component | Status |
|---|---|---|
| 1 | Telegram bot: "What's due this week?" from typed state | ✅ `/due` (no AI) and free-text questions; tested live |
| 2 | Gmail ingestion: extract bills, renewals and price changes | 🟡 Via IMAP and `.eml` ingest rather than the Gmail API/MCP; extraction ✅ (100% type/provider/due date on the eval set) |
| 3 | TinyFish portal check: Agent API reads a bill from a real portal, streamed to chat, plus Browser/Fetch replay | 🟡 The Agent API reads a real page (recorded run) and Fetch works; reading a *bill* portal, streaming to chat, and Browser replay ⏳ |
| 4 | One compiled ability: a repeated task graduates to tested code | ✅ **11** parser versions plus compiled question recognisers, each with held-out tests |
| 5 | AI-free reminders: the scheduler fires reminders with zero LLM calls | ✅ 32 reminders fired from templates in the simulated run |
| 6 | Brain MCP server: Claude Desktop answers "what do I owe?" | ✅ `what_do_i_owe_this_month` prompt, `get_upcoming` tool |

**The seven-step live demo script:**

| Step | Status |
|---|---|
| 01 Connect Gmail; the Brain backfills bills and subscriptions | 🟡 `brain imap --since …` backfills a real inbox; the demo uses the synthetic inbox (`make demo` / `make sim`) |
| 02 Ask on Telegram: "What do I owe this month?" | ✅ |
| 03 Add a portal bill; watch the TinyFish agent read it live | 🟡 `brain portal` (replayed; live with `TINYFISH_LIVE=1`) |
| 04 Show the compiled ability passing its tests and running with no LLM | ✅ The dashboard shows each ability's code, its shown and held-out tests, and its path to active; `uv run pytest abilities` |
| 05 A reminder fires on schedule; the cost counter stays at zero | ✅ |
| 06 Ask Claude Desktop the same question over MCP | ✅ `make mcp` |
| 07 Show live metrics: extraction accuracy, local-code share, cost per message | ✅ Dashboard tiles, the month-by-month view, `brain score`, `make eval` |

---

## Part 2: The design doc, section by section

### Chat channels and data sources (design pp. 5–9)
- ✅ **Telegram as the main channel,** behind one internal message format.
- ⏳ **Discord, WhatsApp** (fixed reminders only).
- ✅ **SMS webhook:**
  - a sender-agnostic OTP filter, so OTPs are dropped and never stored;
  - per-user tokens, so the server accepts only your phone.
- ⏳ **The phone side of SMS:** the Android companion app (Kotlin, WorkManager, signed requests) and the iPhone
  Shortcuts automation.
- 🟡 **Email backfill at setup** (`brain imap --since`). Onboarding questions, the gap-detection Auditor and
  Account Aggregator ⏳.

### State and memory (pp. 10–11)
- ✅ **Typed state:** obligations, subscriptions, documents, medications, source records with hashes.
- ✅ **Episodic memory:** traces and the audit log.
- ✅ **Context packs:** the Chat agent gets a compact typed-state pack, never the inbox.
- ✅ **Confidence + source on every fact;** conflicts are flagged.
- ⏳ **Not built:** embeddings, conversation compaction, and an Event entity separate from obligations (meetings
  are stored as obligations).

### The ability compiler (pp. 11–13)
- ✅ **What an ability is:** name, typed output schema (Pydantic), trigger (sender + subject keywords),
  deterministic Python, permission list, tests from past accepted outputs, a version, and health stats.
- ✅ **The full state diagram:** LLMHandled → Candidate → Generated → Tested → Shadow → Active → Degraded → back
  to the LLM → v2.
- ✅ **Guards:** output validation every run; an overfitting check with held-out cases (≥ 98% required); static
  checks.
- ⏳ **Weekly duplicate-ability merge.**

**Kinds of abilities:**

| Kind | Status |
|---|---|
| Parser | ✅ |
| Scheduled job | ✅ (reminders, medicine doses) |
| Tracker | 🟡 Medicine log in the database; no Google Sheet |
| Report | 🟡 The digest and weekly review (MCP resource/prompt) are fixed code; they are not compiled from repetition |
| Action flow | 🟡 Bill → state → reminder runs as fixed pipeline + rules; meeting request → booking → reminders → reply (with your permission) ➕ |

### Worked example: the Netflix price increase, handled with no AI (pp. 13–15)

| Step | Status |
|---|---|
| 1. Map the inbox: label every email with a type | ✅ The Inbox agent's typed extraction |
| 2. Compile a classifier: exact rules + TF-IDF/LogReg with confidence; low confidence → LLM | ✅ Two-layer classifier; 88.7% held-out accuracy, 100% on confident predictions. Today it short-cuts `ignore` mail only; the other types go to a parser or the LLM |
| 3. Compile an extractor for that sender and type | ✅ The Netflix and Spotify receipt parsers are active |
| 4. A rule as data (`subscription_price_increase`) | ✅ Same rule, same message: *"… is raising your price from ₹… to ₹… on …. Reply KEEP or CANCEL-HELP."* The `calendar_event` action ⏳ (a reminder is used instead) |
| 5. It runs on its own | ✅ Fired for Spotify, Netflix and YouTube in the run |

### Scheduler and AI-free execution (pp. 15–16)
- ✅ **"Remind me…" → the Planner parses it once (LLM) → a durable job.** Job types: one-time, repeating, and
  relative ("7 days before due").
- ✅ **The payload is a template, not a prompt.** Reply handlers (`1`, `done`, `snooze 1h`, `paid`), quiet hours,
  merging of nearby reminders.
- ✅ **The medicine tracker example,** exactly as written: the "thyroid tablet, 1 every morning, 30 left" flow
  with the refill alert at 5.

### Multi-agent orchestration and the harness (pp. 16–17)
- ✅ **Orchestrator, Inbox, Document, Planner, Chat, Compiler agents,** each with an explicit tool list.
- ⏳ **The Auditor.**
- ✅ **Router pattern** (most inputs go to one agent).
- ✅ **Background compiler** (runs at month end / nightly, never in the reply path).
- 🟡 **Verifier:** tests in the sandbox; the extra LLM review ⏳.
- ✅ **Budgets** (per run and per day; the task waits instead of failing). **Model routing** (small vs. strong).
  **Tracing** to the traces table. **Approval gates** (buttons).
- 🟡 **Retries:** one Pydantic repair retry; general backoff and loop detection ⏳.

### MCP: using servers and being one (pp. 18–19)

| Design tool / feature | Status |
|---|---|
| `get_upcoming(days, type?)` | ✅ |
| `get_obligation(id)` / `search_obligations(query)` | ✅ |
| `mark_paid(id)`, `create_reminder(text, when)` | ✅ (write, audit-logged) |
| `list_abilities()`, `run_ability(name, input)` | ✅ (active abilities only, sandboxed) |
| `get_privacy_score` | ➕ |
| `get_spending_trend`, `get_med_schedule`, `add_obligation` | ⏳ |
| Resources: profile summary, monthly digest | ✅ `sorted://profile`, `sorted://digest` |
| Prompts: "weekly review", "what do I owe this month" | ✅ |
| Streamable HTTP with an access token | ✅ Bearer token + read / read-write scope |
| Per-client tokens, rate limits | ⏳ |
| Using Gmail / Calendar / Drive MCP servers as a client | ⏳ |

### Privacy and security (pp. 19–21)
- ✅ **Redaction first** (emails, cards, phones, account/policy numbers), enforced inside the LLM wrapper.
- ✅ **Minimum context.** **Shrinking exposure:** an active ability's sender never reaches an LLM again.
- ✅ **No paying, forwarding or deleting; no messaging others.** The single exception is the meeting reply, which
  is sent only on your button press, into an outbox.
- ✅ **Sandbox and static checks for generated code.** An audit trail of every action.
- ✅ **The privacy score,** "measurable instead of a promise", reported monthly.
- ⏳ **Not built:** encryption at rest, retention/deletion of raw bodies (redacted text is kept), and a local
  model option (Ollama).

### Evals and metrics (pp. 22–23)

| Metric (design target) | Measured (synthetic data) |
|---|---|
| Field extraction accuracy (≥ 95%) | ✅ type / provider / due date 100%, amount 98.6% (77 messages) |
| Local-code share (rising each month) | 🟡 0 → 0 → 7 → 0 → 62 → 47%: rising, with the shadow and layout-change dips explained above |
| Cost per processed message (falling each month) | 🟡 Falls after the compile month (see slide 8) |
| Ability pass rate on held-out cases (≥ 98% before activation) | ✅ Enforced as a gate; every activated ability passed 100% of its held-out cases |
| Ability fallback rate (low and stable) | ✅ 1 fallback in the run (HDFC layout change), repaired by v2 |
| Reminder on-time rate (≥ 99%) | 🟡 Reminders fire on the simulated clock; real-time on-time rate not measured |
| Missed obligations, user correction rate | ⏳ Not measured |

- **Eval sets:** extraction ✅ (81 labelled synthetic messages; the design asked for 100–200 *real* ones ⏳);
  ability held-out ✅; safety ✅ (phishing/injection sample); chat set ⏳.
- **Ablations** (redaction on/off, small vs. large model, 3 vs. 5 repetitions, shadow on/off) ⏳.

### Build roadmap (pp. 24–25), phase by phase

| Phase | Done when (design) | Status |
|---|---|---|
| 0. Foundations | Eval set exists | ✅ (synthetic) |
| 1. Single agent | Ask "What's due this week?" and get a correct answer | ✅ |
| 2. Scheduler | A 9 PM reminder fires with no LLM call | ✅ (Calendar MCP ⏳) |
| 3. Brain MCP server | Claude Desktop answers from your state | ✅ |
| 4. Multi-agent | A 500-email backfill survives a crash and resumes | 🟡 Agents ✅; budgets/queue/drain ✅; step-level checkpointing ⏳ |
| 5. Ability compiler | Top 5 senders run on compiled parsers | ✅ 9 senders active in the run |
| 6. SMS on both phones | Bank SMS from both phones appear in state within a minute | 🟡 Webhook ✅; phone apps ⏳ |
| 7. Measure and publish | A public repo with real before-and-after numbers | 🟡 Public repo, dashboard and privacy score ✅; numbers are from synthetic data, real-inbox numbers ⏳ |

---

## Part 3: Built, and not in the proposal (➕)

- **Compiled chat questions.** Repeated question types get a compiled, tested recogniser, so "do I have any
  doctor appointments this month?" is answered with 0 AI calls.
- **Sorted notices new kinds of messages by itself.** After every message, it re-assesses whether a new category
  (e.g. shipment requests) has repeated, then proposes a skill. The skill is limited to a safe action list, and
  parsers are compiled only after you agree.
- **The meeting-request flow:**
  - you choose the proposed slot, type another time, or decline;
  - reminders, a Google Meet link and a Google Calendar link;
  - a reply to the person, sent only on your button press.
- **Date-range digests:** "all my dues and updates between 1 August and 15 September".
- **Synthetic data on demand:** describe a scenario, and the AI writes the messages into the simulation.
- **An interactive simulation:**
  - a FastAPI dashboard with a privacy panel, **month-by-month highlights** of what was learned, *Skills learned
    so far*, each ability's code and tests, and a live feed;
  - the same simulation in Telegram;
  - a one-command **`/run` autopilot** whose pace can change mid-run (`/fast`).
- **A record/replay LLM cache,** so the full demo runs offline with no API key, with dates shifted so the
  timeline always ends today.
- **Abilities exported** as standalone code plus pytest files ([`abilities/`](../abilities)) that anyone can read
  and run.

## Part 4: Still to build (⏳), in order of priority

1. **Real-inbox evaluation:** run on a real inbox over IMAP and report real accuracy and privacy share.
2. **TinyFish portal graduation:** Agent run → compiled Playwright script → scheduled Browser-API replay → fallback.
3. **Docker `--network none` sandbox.**
4. **Google Calendar API:** real events and real Meet links instead of prefilled links.
5. **Per-client MCP tokens and rate limits;** Gmail/Calendar MCP client side.
6. **Android SMS companion app and iPhone Shortcut.**
7. **Encryption at rest,** retention of raw bodies, and Ollama for local extraction.
8. **The Auditor agent** (missing bills, duplicate charges), the weekly ability merge, and habit learning.
9. **OCR for photos;** WhatsApp/Discord; Account Aggregator; family mode.

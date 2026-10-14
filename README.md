# Sorted

**A household admin assistant that uses AI as a compiler, not an interpreter.** It learns a task with an LLM,
then writes, tests and switches to its own local code, so it gets cheaper, faster and more private every month.

*AzinHack 2026 · Team Not Found: Anish Manchanda, Aryan Thakur, Keshav Goel*

## The problem

In an Indian household, one person usually keeps track of everything: credit card bills, BSES/electricity,
broadband, LIC premiums, car insurance renewals, Netflix price hikes, Mom's thyroid tablets, the PUC certificate.
The information is spread across email, SMS, PDFs and memory, and each app sees only one slice. Things slip.

A typical "AI assistant" fixes this by sending every email to an LLM, every time. That is slow, costs money on
every message and sends your bank statements to a model provider forever.

Sorted uses the LLM only while a task is **new**. Every LLM solve is saved as a trace. When the same kind of
message repeats (3 times by default), a compiler agent writes a small Python parser plus tests from those traces.
The parser is checked, tested in a sandbox against held-out cases, approved by you, run in shadow next to the LLM,
and then takes over with **zero LLM calls**. If a bank changes its email layout, validation fails, Sorted falls
back to the LLM, collects new traces and compiles **version 2**. Everything is queryable from Claude Desktop or
Cursor through an MCP server.

## Results (real numbers, from `make demo` and `make eval`)

The demo replays six months of a synthetic household inbox: 76 messages (54 emails, 19 SMS, 3 PDFs). Every
figure below is copied from [`reports/demo_run.md`](reports/demo_run.md) and [`reports/eval.md`](reports/eval.md).

| simulated month | messages | handled by local code | LLM calls | tokens | privacy score | cost / message (USD, est.) |
|---|---|---|---|---|---|---|
| Apr 2026 | 10 | 0 | 10 | 9,962 | 0% | 0.00045 |
| May 2026 | 12 | 0 | 12 | 12,999 | 0% | 0.00050 |
| Jun 2026 | 14 | 1 | 22 | 24,552 | 7% | 0.00576 |
| Jul 2026 | 12 | 0 | 12 | 11,662 | 0% | 0.00044 |
| Aug 2026 | 12 | 9 | 4 | 3,806 | **75%** | 0.00068 |
| Sep 2026 | 12 | 8 | 5 | 5,867 | **67%** | 0.00129 |

- June: 9 abilities compiled. Its LLM calls include the compiler agent (strong model), so its cost per message
  is the highest. July is the shadow month: abilities run next to the LLM, and the LLM's answer is still used.
- Sep: HDFC redesigns its statement email. `hdfcbank_net_bill_due@v1` fails validation ("Missing Payment Due
  Date"), the message falls back to the LLM and v2 is compiled from the old cases plus the new layout. The v2
  compile is part of September's cost.
- 11 ability versions compiled, each passing all its visible tests and 100% of its held-out cases. The code is in
  [`abilities/`](abilities). `uv run pytest abilities` runs their 35 generated tests.
- **Extraction accuracy:** 100% on type, provider, amount and due date for all 72 non-OTP samples, for both the
  LLM route and the compiled code (17 compiled-code extractions). The data is synthetic and template-generated,
  so real inboxes will be harder. We will report real-inbox numbers when we have them.
- **Local ML classifier** (TF-IDF + logistic regression, held-out): 90.0% accuracy over 5 stratified 70/30
  splits. 83.6% of predictions clear the 0.7 confidence threshold, and those are 100% correct; everything
  below the threshold goes to the LLM. In the six-month demo it starts empty and learns only from the LLM's
  labels, so with so few examples it never clears the threshold (closest: the Amazon promo at 0.49 for
  `ignore`) and correctly defers to the LLM.
- **Rules fire with no LLM:** Spotify ₹119→₹139, Netflix ₹499→₹649 and YouTube ₹129→₹149 each produced a chat
  alert and a reminder 2 days before the new price.
- **Safety:** the prompt-injection email never reaches an LLM. OTP SMS are dropped before storage.
- 51 offline tests (`make test`).

## Quickstart

Python 3.12 and [uv](https://docs.astral.sh/uv/) required.

```bash
git clone <this repo> && cd sorted
make setup      # installs deps, creates .env from .env.example, creates the SQLite DB
make demo       # six simulated months end to end -> reports/demo_run.md (no API key needed)
make eval       # extraction accuracy per handler + classifier held-out accuracy -> reports/eval.md
make test       # 51 offline tests (LLM and TinyFish mocked)
```

`make demo` replays the LLM responses recorded in [`data/llm_cache/`](data/llm_cache) during our live run.
The output is identical to the live run and needs no key. To run against live models, put `OPENAI_API_KEY`
and/or `CEREBRAS_API_KEY` in `.env` (optionally `TINYFISH_API_KEY`) and run `make demo-live`. Either key alone
works: each route falls back to the other provider.

Other entry points:

```bash
uv run brain ingest data/samples/email/2026-04_bses.eml   # any .eml or .pdf through the pipeline
uv run brain say "Track Mom's thyroid tablet, 1 every morning, 30 left"
uv run brain due              # what's due in the next 7 days (no LLM)
uv run brain ask "When does my car insurance expire?"
uv run brain abilities        # compiled abilities + health
uv run brain approve <name>   # human gate: tested -> shadow
uv run brain score            # privacy score per month
uv run brain fetch <url>      # TinyFish Fetch a page into the pipeline
uv run brain portal <url> "<goal>"   # TinyFish Agent (replays unless TINYFISH_LIVE=1)
uv run brain imap --since 2026-10-01 # read-only IMAP (Gmail app password)
make bot        # Telegram bot + scheduler
make mcp        # Brain MCP server over stdio
```

## Architecture

```mermaid
flowchart TD
    subgraph Sources
        EM[Email: fixtures / IMAP]
        SMS[SMS webhook POST /ingest/sms]
        PDF[PDF upload / Telegram]
        WEB[TinyFish Fetch + Agent]
    end
    EM & SMS & PDF & WEB --> F[OTP filter, redaction, injection guard]
    F --> ORCH[Orchestrator]
    ORCH -->|trigger matches an active ability| RUN[Ability runtime: sandboxed local code, no LLM]
    ORCH -->|confident 'ignore'| ML[Local classifier: rules + TF-IDF/LogReg]
    ORCH -->|otherwise| AG[Inbox / Document agents: small LLM route]
    AG --> TR[(Traces)]
    TR --> DET[Pattern detector] --> COMP[Compiler agent: strong LLM route]
    COMP --> CHK[AST static check + sandbox tests + held-out cases] --> REG[Ability registry]
    REG -->|you approve; shadow; active| RUN
    RUN & AG --> VAL[Output validation]
    VAL --> ST[(SQLite state store)]
    ST --> RULES[YAML rules] --> SCH[APScheduler reminders]
    SCH --> TG[Telegram bot]
    TG -->|free text| CHAT[Chat agent: state only]
    TG --> ORCH
    ST & REG --> MCPS[Brain MCP server] --> EXT[Claude Desktop / Cursor / any MCP client]
```

The graduation pipeline, as implemented in `brain/compiler/`:

```mermaid
stateDiagram-v2
    [*] --> LLMHandled
    LLMHandled --> Candidate: 3 accepted traces, same sender + type
    Candidate --> Generated: compiler agent writes code
    Generated --> Candidate: static check or tests fail (after one retry)
    Generated --> Tested: all visible + >= 98% held-out cases pass
    Tested --> Shadow: you approve (/approve or brain approve)
    Shadow --> Active: matches the LLM for N runs
    Shadow --> Degraded: mismatch
    Active --> Degraded: output fails validation / extraction empty
    Degraded --> Candidate: new traces -> compile v(n+1), old version kept
```

How one message flows:

1. A source adapter turns it into one internal `Message`. OTPs are dropped before anything is stored.
2. The text is redacted (cards keep their last 4 digits; account numbers, phones and emails are masked). Agents,
   compiled abilities and the compiler all see only the redacted text.
3. The orchestrator checks the ability registry. An **active** ability whose trigger matches (sender + subject
   keywords) runs in the sandbox with no LLM. A **shadow** ability runs next to the LLM and is compared with it.
4. Otherwise the local classifier may decide a confident `ignore`. If not, the Inbox or Document agent extracts
   typed fields with the small LLM route, and the run is saved as a trace.
5. Output validation runs (amount > 0, due date in a sensible window, provider present). Failures lower confidence
   and flag the item. Duplicates (the bank's email and its SMS) are linked; conflicts (two premiums for one
   renewal) are flagged, never overwritten. Every fact points at the `source_records` row it came from.
6. YAML rules run (no LLM), and relative reminders are scheduled ("3 days before due").
7. In the background, the detector groups traces and the compiler turns repeats into abilities.

## Role of AI / ML

| Where | What | Model |
|---|---|---|
| Extraction and classification of new message types | Inbox and Document agents, JSON validated by Pydantic, one repair retry | Small route: Cerebras `gpt-oss-120b` (env-configurable) |
| Chat answers | Chat agent answers from a typed state "context pack", never raw email | Small route |
| Requests to the Planner | "Track Mom's thyroid tablet…" parsed once into a medication plus a cron job | Small route |
| Writing code | Compiler agent writes a parser from traces; static check, sandbox tests and held-out cases decide | Strong route: OpenAI `gpt-5.4` |
| Repair | Same compiler, fed the failing new layout + the old cases | Strong route |
| **Local ML** | Two-layer email-type classifier: exact sender/subject rules, then **TF-IDF + LogisticRegression** (scikit-learn), retrained on every LLM-labelled message; below the 0.7 confidence threshold the message goes to the LLM | Runs locally, no network |
| Compiled abilities | Deterministic Python, no AI at run time | None |

`brain/llm.py` is one small wrapper for both providers through the official `openai` SDK (Cerebras is
OpenAI-compatible). It handles JSON mode, Pydantic validation, one retry carrying the validation error, redaction
of every prompt, token and cost logging to `traces`, per-run and per-day token budgets (over budget, the
message is **queued**, not failed; `brain drain` retries it), and record/replay. Model IDs come only from env and
were checked against `client.models.list()` for our keys.

## TinyFish integration

`brain/sources/tinyfish.py` uses the documented REST endpoints with `X-API-Key` (verified against
[docs.tinyfish.ai](https://docs.tinyfish.ai/for-coding-agents.md)):

- **Fetch API** (`POST https://api.fetch.tinyfish.ai`, free): `brain fetch <url>` turns any page (a bill page,
  a public pricing page) into a `web` message that goes through exactly the same pipeline as email: redaction,
  agents, validation, traces, compiler. `--expect-price 649` checks a price-change email against the provider's
  public page.
- **Agent API** (`POST https://agent.tinyfish.ai/v1/automation/run` with `output_schema`, uses credits):
  `brain portal <url> "<goal>"` and Telegram `/portal`. Every run is stored as a `portal` trace, so it can
  graduate like any other task. A result with `amount_due` + `due_date` becomes a bill obligation.
- **Search API** (free): `search()` helper to find a biller's official site.
- Credits: tests never call the Agent API; they mock HTTP. By default (`TINYFISH_LIVE=0`) Agent runs **replay**
  recorded responses from [`tests/fixtures/tinyfish/`](tests/fixtures/tinyfish). We recorded one real run
  (3 steps, 13 s, Netflix's public plans page → `{plan: Standard, price: 19.99, currency: USD}`; TinyFish
  proxies have no India exit, so that page shows US pricing). Steps used are printed when the API reports them.
- With no `TINYFISH_API_KEY`, every call returns a clear "not configured" message, and the demo still runs
  because the Agent step replays.

**Planned: graduation for the web (not built yet).** The same compiler idea applied to portals:

1. **Agent run**: TinyFish Agent solves "get the amount due from this portal" with an output schema (built,
   stored as a trace).
2. **Compile to a script**: after 3 successful runs, the compiler turns the agent's recorded steps into a
   Browser API / Playwright script plus tests.
3. **Replay on schedule**: the scheduler runs that script monthly with no agent and no LLM.
4. **Fall back when the page changes**: script fails validation → one Agent run → recompile v2.

## Telegram bot

```bash
make bot   # needs TELEGRAM_BOT_TOKEN (from @BotFather) in .env
```

The first chat to send `/start` becomes the owner, or set `TELEGRAM_OWNER_ID`. Every other chat is ignored.

- Commands: `/due` (next 7 days, no LLM), `/score`, `/abilities`, `/approve <name>`, `/audit`, `/portal <url>`.
- Reply rules, no LLM: `1` / `done` logs a dose and lowers stock (at ≤ 5 left, the `medicine_refill` rule sends
  a refill alert), `snooze 1h`, `paid [provider]`.
- "Track …" / "Remind me …" goes to the Planner, which makes one LLM call. The jobs it creates fire with fixed
  templates and no LLM.
- Other questions go to the Chat agent, which answers from state only. PDFs sent to the bot go to the Document
  agent. Photo OCR is on the roadmap.
- Background jobs in the bot process: reminders (APScheduler, SQLAlchemy job store, survives restarts),
  quiet hours (`BRAIN_QUIET_HOURS=22-07`), reminders due within 15 minutes merged into one message, a nightly
  compile + classifier retrain (it never auto-approves), and IMAP polling when configured.

## Brain MCP server (Claude Desktop, Cursor)

Built on the official MCP Python SDK (v2, `MCPServer`).

- **Tools:** `get_upcoming(days, type?)`, `search_obligations(query)`, `get_obligation(id)` (with source link),
  `mark_paid(id)` (write, logged), `create_reminder(text, when)` (write, logged), `list_abilities()` (health
  stats), `run_ability(name, input)` (active abilities only, sandboxed), `get_privacy_score()`.
- **Resources:** `sorted://profile`, `sorted://digest` (monthly digest).
- **Prompts:** `weekly_review`, `what_do_i_owe_this_month`.

Claude Desktop → Settings → Developer → Edit Config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sorted": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/sorted", "run", "python", "-m", "brain.mcp_server"]
    }
  }
}
```

If Claude Desktop cannot find `uv`, use its absolute path (`which uv`). Run `make demo` first so there is state to
query, then ask Claude "What do I need to pay this week?".

Remote clients: `make mcp-http` serves Streamable HTTP at `http://127.0.0.1:8765/mcp`. It requires
`Authorization: Bearer $BRAIN_MCP_TOKEN`, and `BRAIN_MCP_SCOPE=read` disables the write tools.

## SMS: webhook, Android and iPhone

`brain serve-sms` runs `POST /ingest/sms` (FastAPI) with per-user bearer tokens from `BRAIN_INGEST_TOKENS`
(`name:token,…`). The body is `{"sender": "VM-HDFCBK", "body": "...", "received_at": "<ISO, optional>"}`. OTPs are
dropped server-side before storage.

- **iPhone (planned, documented):** Shortcuts → Automation → *Message* trigger filtered on words like "debited",
  "due", "premium" → action *Get Contents of URL* → POST, JSON body `{sender: Shortcut Input sender, body:
  Shortcut Input content}`, header `Authorization: Bearer <your token>`. The server must be reachable from the
  phone (e.g. Tailscale or a tunnel).
- **Android (planned):** a small companion app with a sender allowlist and OTP filter, posting to the same
  endpoint.

## Implementation by module

| Module | What it does |
|---|---|
| `brain/db.py` | SQLAlchemy 2.0 models: `obligations`, `subscriptions`, `medications`, `dose_log`, `documents`, `source_records`, `traces`, `abilities`, `ability_tests`, `audit_log`; APScheduler keeps `apscheduler_jobs` in the same SQLite file |
| `brain/messages.py`, `brain/sources/` | One `Message` format; adapters for fixtures, IMAP (read-only), SMS webhook, PDF (pdfplumber), TinyFish |
| `brain/filters.py`, `brain/redact.py` | OTP filter, prompt-injection guard, regex redaction (unit-tested) |
| `brain/llm.py` | Two-route LLM wrapper (OpenAI SDK for OpenAI + Cerebras), budgets, cost, record/replay |
| `brain/agents.py`, `brain/planner.py`, `brain/orchestrator.py` | Plain-class agents with explicit tool lists; no agent can send to others, pay, forward or delete |
| `brain/validate.py`, `brain/state.py` | Pydantic `Extraction` schema, output rules, duplicate linking and conflict flagging |
| `brain/compiler/` | `detector` (candidates), `generator` (compiler agent + tests + held-out split), `static_check` (AST allowlist), `sandbox` (subprocess, empty env, sockets blocked, rlimits, timeout), `registry` (match / shadow / activate / degrade / approve) |
| `brain/rules/` | Rules as YAML data with a fixed action set and permissions: `subscription_price_increase`, `subscription_price_update`, `medicine_refill` |
| `brain/ml/` | Local classifier (rules + TF-IDF/LogReg), `python -m brain.ml.train` (`make train`) |
| `brain/scheduler.py`, `brain/replies.py`, `brain/notify.py` | Durable reminders, quiet hours, merging, rule-based replies, the user-only outbound channel |
| `brain/score.py`, `brain/eval.py` | Privacy score + cost per message; extraction accuracy per handler, classifier held-out accuracy |
| `brain/telegram_bot.py`, `brain/mcp_server.py` | Channels |
| `brain/demo.py` | The six-month simulation behind `make demo` |
| `scripts/gen_samples.py` | Generates the synthetic inbox and its labels (`make samples`) |

## Safety and privacy

- Message text is always data. The extraction prompt says so, but the real defence is structural: **no tool
  exists** to message other people, pay, forward or delete. The only outbound channel is a message to the
  user themself. A regex guard also keeps obvious injection text away from the LLM (tested on the sample).
- Redaction runs before any LLM call, inside the wrapper, so no caller can skip it.
- Generated code must pass an AST allowlist (`re`, `datetime`, `decimal`, `html`, `json`, `dateutil` only;
  no `open`/`eval`/`exec`/`__import__`/dunder access/`os`/`socket`/…). It runs only in a separate process with an
  empty environment (no API keys), sockets disabled, CPU/file-size limits and a timeout. A test proves a
  malicious sample is rejected, a test proves the sandbox times out, and a test proves it has no network or
  secrets even if the checker were bypassed.
- Human gate: no ability leaves `tested` without your approval. The demo auto-approves and prints that it did.
- Every write (mark paid, reminders, abilities, rules) is in `audit_log` (`/audit`).
- `.env`, the SQLite DB, uploads and models are git-ignored. All sample data is synthetic: fake names, card,
  account and policy numbers.

## What's built vs. planned

| Area | Status |
|---|---|
| Ingestion: fixtures, IMAP (read-only), SMS webhook with bearer tokens, PDF upload | Built |
| OTP filter, redaction, injection guard, validation, conflict flagging | Built |
| Two-route LLM wrapper (OpenAI + Cerebras), budgets, queueing, record/replay | Built |
| Ability compiler: detector, compiler agent, AST check, subprocess sandbox, held-out tests, approval, shadow, active, degraded → v2 | Built |
| Rules as YAML (price increase, price update, medicine refill) | Built |
| Local ML classifier (TF-IDF + LogReg) with confidence threshold | Built |
| Privacy score and cost per message | Built (`brain score`, `/score`, MCP) |
| Scheduler: one-time, cron, relative; quiet hours; merging | Built |
| Telegram bot, medicine tracker, reply handlers | Built (smoke-tested start-up; commands unit-tested) |
| Brain MCP server (stdio + Streamable HTTP with bearer token and scope) | Built |
| TinyFish Fetch / Agent / Search adapter | Built (one real Agent run recorded; Fetch and Search tested live) |
| TinyFish web graduation (Agent → Playwright/Browser API script → scheduled replay → fallback) | Planned |
| Docker `--network none` sandbox | Planned (process-level sandbox today) |
| Android SMS companion app, iPhone Shortcut | Planned (webhook built and documented) |
| WhatsApp / Discord channels | Planned |
| Gmail MCP / Google Calendar MCP clients | Planned (IMAP today; reminders instead of calendar events) |
| Photo OCR (Tesseract / vision model) | Planned (text PDFs today) |
| SQLCipher / field-level encryption, Postgres, sqlite-vec embeddings | Planned |
| Langfuse / OpenTelemetry tracing | Planned (traces table today) |
| Per-client MCP tokens, rate limits | Planned (one token + scope today) |
| Weekly duplicate-ability merge, habit learning, Auditor agent | Planned |
| Account Aggregator bank data, family mode, hosted version | Planned |

## Roadmap

Next (in-person round, 21–22 Oct): run the bot and MCP server against a real inbox and measure real-inbox
accuracy, the Docker sandbox, TinyFish portal graduation, and Google Calendar events for reminders.

Later: the Android SMS app and iPhone Shortcut, WhatsApp reminder templates, encryption at rest, the Auditor agent
(missing bills, duplicate charges), and Account Aggregator.

## Team

**Team Not Found:** Anish Manchanda, Aryan Thakur, Keshav Goel.

# 00: Brief, scope and hard rules

## The product in one paragraph

**Sorted** is a household-admin assistant for Indian families. It reads bills, renewals, insurance premiums,
subscriptions, appointments, meeting requests, documents and medicine schedules from email, SMS, PDFs, the web and
chat, and keeps them as typed facts. It reminds you on Telegram and answers questions there and over MCP.

Its difference is **"AI as a compiler, not an interpreter"**:
- the LLM handles a new kind of task, and every solve is saved as a trace;
- when a task repeats, a compiler agent writes deterministic Python plus tests;
- the code is checked statically, run in a sandbox against held-out cases, approved by the user, run in shadow
  next to the LLM, and then takes over with **zero LLM calls**;
- when the code breaks, the task falls back to the LLM and version 2 is compiled.

The share of work done by local code is reported as a **privacy score**.

Team: Team Not Found (Anish Manchanda, Aryan Thakur, Keshav Goel). Event: HackIIITD / AzinHack 2026, IIIT Delhi.
The PDFs call the project "Personal Admin Brain"; the built project is **Sorted** (package `brain`, CLI `brain`).

## Hard rules (non-negotiable)

1. **Secrets and personal data never go into git.** Write `.gitignore` before anything else. It must cover:
   - `.env`, `*.db`, `*.db-journal`, `*.db.bak*`;
   - `data/raw/`, `data/models/`, `data/demo/`, `data/abilities/`, `data/telegram_owner`;
   - the usual Python caches and `.venv/`.

   All sample data is synthetic (fake people, numbers and amounts).
2. **Tests run offline.** No test may call an LLM, TinyFish or any HTTP endpoint. Use a `FakeLLM` (see 09).
   Never call the TinyFish Agent API in a test or in a loop; it costs credits.
3. **No agent and no LLM tool can send to other people, pay, forward or delete.** Every agent class declares a
   `TOOLS` tuple, and a test asserts no tool name contains `send`, `pay`, `forward`, `delete` or `email.write`.
   - **The one message to another person** is the meeting-request reply. It is a template, sent only when the user
     presses Send, and "sent" means written to an outbox (the audit log); there is no mail server.
4. **Redaction happens inside the LLM wrapper,** so no caller can forget it.
5. **Side effects run after the database commit:** reminders, chat alerts and asks. Never inside the transaction.
6. **The README states only what the code does,** and every number in it is copied from `reports/`.
7. **Model IDs and prices live only in env** (`.env.example`), never hardcoded.
8. **Generated code is untrusted:** AST check, separate process, no network, no secrets in its environment, held-out
   tests, human approval, shadow mode.

## Where the build deliberately differs from the PDFs

The design PDF describes a 12-week vision. The build is the hackathon version; where they differ, follow the
build:

| PDF says | Build does | Why |
|---|---|---|
| Claude API via a router; Ollama local | Two routes through the `openai` SDK: `small` = Cerebras `gpt-oss-120b`, `strong` = OpenAI `gpt-5.4`, falling back to the other provider when a key is missing | Keys we had; Cerebras is fast and cheap for high-volume extraction |
| Gmail MCP client | Read-only IMAP (`imaplib`) and `.eml` files | No OAuth app review needed; Gmail works with an app password |
| Docker `--network none` sandbox | A subprocess with an empty environment, sockets monkey-patched to raise, rlimits, a temp working directory and a timeout | Hackathon time; Docker is the planned upgrade (marked `ponytail:` in the code) |
| SQLCipher, sqlite-vec, Postgres | Plain SQLite via SQLAlchemy 2.0 | Scope |
| Calendar events via the Calendar MCP | A prefilled Google Calendar link + an `.ics` file; a placeholder Meet link | No OAuth |
| Langfuse / OpenTelemetry | A `traces` table + an `audit_log` table | Scope |
| Auditor agent, weekly ability merge, habit learning | Not built | Scope |
| Android SMS app / iPhone Shortcut | Only the server side: `POST /ingest/sms` with per-user bearer tokens | Scope |
| Discord, WhatsApp, OCR, Account Aggregator, family mode | Not built | Scope |
| TinyFish: Agent → compiled Playwright script → Browser-API replay | Fetch, Search and Agent adapters; one recorded Agent run replayed offline; no script compilation | Scope; next milestone |
| Classifier decides every type | The classifier only short-circuits a confident `ignore`; every other type goes to a parser or the LLM | Safety: wrong money facts are worse than an LLM call |

**Added beyond the PDFs** (all specified in this kit):
- compiled chat questions;
- automatic discovery of new message categories, turned into user-approved skills;
- the meeting-request flow (pick a time, Meet + Calendar links, a reply only with permission);
- date-range digests;
- synthetic data generated from a description;
- an interactive six-month simulation with a web dashboard, a Telegram front end and a one-command autopilot;
- a record/replay LLM cache with date shifting, so the demo runs with no API key.

## Stack

- **Core:** Python ≥ 3.12, managed with `uv`, build backend `hatchling`, package `brain`, console script
  `brain = "brain.cli:main"`.
- **Runtime dependencies:** `sqlalchemy>=2.0`, `pydantic>=2.7`, `python-dotenv`, `python-dateutil`, `openai>=1.40`,
  `fastapi`, `uvicorn`, `pdfplumber`, `pyyaml`, `apscheduler>=3.10,<4`, `scikit-learn`, `joblib`,
  `python-telegram-bot>=21`, `mcp>=2.3.0` (official SDK; `from mcp.server.mcpserver import MCPServer`), `fpdf2`
  (writes the sample PDFs).
- **Dev dependencies:** `pytest>=8`, `ruff`, `httpx`.
- **Ruff:** line length 120, target py312, rules `E,F,I,B,UP`, ignore `B008`.
- **Pytest:** `testpaths=["tests"]`, `addopts="--import-mode=importlib"`.
- **Timezone:** everything is IST (`Asia/Kolkata`). Datetimes are stored naive in IST.

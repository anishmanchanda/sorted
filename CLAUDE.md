# CLAUDE.md

Context for future Claude Code sessions on **Sorted** (AzinHack 2026, Team Not Found: Anish Manchanda, Aryan Thakur,
Keshav Goel). Repo: https://github.com/anishmanchanda/sorted. Online submission closed 18 Oct 2026; the in-person
round is 21–22 Oct 2026. `README.md` is the judge-facing doc; `docs/design.pdf` is the full 12-week design.

## What it is

A household-admin assistant (bills, renewals, subscriptions, medicines, document expiry) that uses **AI as a
compiler, not an interpreter**:
1. The LLM handles a new kind of message, and each solve is saved as a trace.
2. After 3 accepted traces for the same sender and type, a compiler agent writes a Python parser plus tests.
3. The parser goes through an AST check, sandbox tests and held-out cases, then human approval, then shadow mode,
   and finally becomes **active**: it runs with zero LLM calls.
4. When a parser later fails validation, the message falls back to the LLM and v2 is compiled.

Channels: a Telegram bot and an MCP server for Claude Desktop and Cursor.

## Commands

```bash
make setup        # uv sync, .env from .env.example, init data/brain.db
make test         # 54 offline tests (LLM/TinyFish/HTTP mocked) — keep them offline
make lint         # ruff (line length 120)
make demo         # synthetic 6-month simulation -> reports/demo_run.md, data/demo.db; replays data/llm_cache (no key)
make demo-live    # same, every LLM call live (does NOT record to the cache)
make eval         # re-score the last demo -> reports/eval.md (needs data/demo.db)
make train        # retrain local classifier (live DB traces + labelled samples)
make samples      # regenerate committed canonical fixtures in data/samples (fixed 2026 dates; used by tests)
make bot          # Telegram bot + scheduler (live DB)
make mcp          # MCP server over stdio; make mcp-http = Streamable HTTP + bearer token
uv run brain --help   # CLI: ingest, say, ask, due, compile, approve, abilities, score [--demo], fetch, portal, imap, drain, serve-sms
uv run pytest abilities   # the 36 tests the compiler generated for its own parsers
```

## Map

- `brain/orchestrator.py`: the core flow. OTP filter → store the source (redacted text) → injection guard →
  active ability → local classifier (a confident `ignore` skips the LLM) → agent (LLM) → validate →
  `state.apply` → rules → trace. Side effects (reminders, alerts) run **after commit**, through
  `out["after_commit"]`.
- `brain/llm.py`: two routes (`small` = Cerebras gpt-oss-120b, `strong` = OpenAI gpt-5.4) via the `openai` SDK.
  Handles JSON mode with one Pydantic repair retry, redacts every prompt, enforces token budgets
  (`BudgetExceeded` → the source is queued), and does record/replay through `BRAIN_LLM_CACHE`.
- `brain/compiler/`: `detector`, `generator` (compiler agent, held-out split, export to `abilities/`),
  `static_check`, `sandbox` (subprocess, empty env, no sockets), `registry` (lifecycle).
- `brain/agents.py`, `brain/planner.py`: agents are plain classes with a `TOOLS` tuple. **No tool may send to
  others, pay, forward or delete.** A test enforces this.
- `brain/rules/*.yaml`: rules as data, with a fixed action set and permissions.
- `brain/ml/`: TF-IDF + LogReg classifier. `brain/scheduler.py`: APScheduler with the SQLAlchemy job store.
- `brain/sources/`: fixtures, IMAP, the SMS webhook, PDF, and TinyFish (Agent replays from
  `tests/fixtures/tinyfish/` unless `TINYFISH_LIVE=1`).
- `brain/demo.py`, `brain/samples.py`: the simulation and the synthetic data generator.
- `brain/telegram_bot.py`, `brain/mcp_server.py`: the channels. Bot logic lives in pure functions so it can be
  tested.

## Things that will bite you

- **Two databases.** `data/brain.db` is live (bot, MCP, CLI). `data/demo.db` is the simulation. `demo.py` sets
  `BRAIN_DB_URL` and the other env vars **before importing `brain`**, because `config`, `db.engine` and
  `classifier.MODEL_PATH` read env at import time. Never point the demo at the live DB.
- **Demo dates are relative to the run date.** Sample ids are `m1_…` to `m6_…` ("Sim month N"), detected by
  `messages.sim_sample()`. `score` groups those by Sim month and real data by calendar month.
- **Replay cache.** Demo LLM calls use semantic keys (`extract:<sample_id>`,
  `compile:<name>:v<n>:n<traces>:attempt<k>`) hashed together with the system prompt. Replayed ISO dates shift
  by `BRAIN_DATE_OFFSET` relative to the recorded offset. **Changing a system prompt invalidates the cache:**
  delete `data/llm_cache/`, run `make demo` with keys (it records live on a miss), commit the new cache plus
  `reports/` and `abilities/`, then update the README numbers from `reports/`. A full re-record is about 69
  calls and costs roughly $0.10–0.15.
- **README numbers must come from `reports/`.** Never invent them. LLM variance changes them on every
  re-record.
- `pytest` uses `--import-mode=importlib`. `tests/conftest.py` sets an in-memory DB (`StaticPool`), an empty
  cache, and temp model/abilities dirs. `FakeLLM.json` must accept `cache_key`.
- Generated parsers may import only `re`, `datetime`, `decimal`, `html`, `json`, `dateutil`, `typing`.
- Model IDs and prices live only in env (`.env.example`). `BRAIN_PRICES` costs are **estimates**.
- `.env`, `*.db`, `*.db.bak*`, `data/demo/`, `data/raw/`, `data/models/`, `data/abilities/` and
  `data/telegram_owner` are git-ignored. Never commit keys or real personal data; all samples are synthetic.
- The bot owner is the first chat to send `/start` (stored in `data/telegram_owner`), or `TELEGRAM_OWNER_ID`.
- Commit authorship so far: `Anish Manchanda <anishmanchanda2006@gmail.com>`.

## Status

Built: everything in M0–M8 of the brief (see the README's "What's built vs. planned" table). The bot has been
tested live in Telegram. The MCP server has been tested end to end with the official client over stdio. One real
TinyFish Agent run is recorded.

Latest recorded simulation:
- 0% local code in Sim months 1–2, 67% in Sim months 5–6.
- 11 ability versions compiled, including HDFC v2 after the layout change.
- Extraction accuracy: compiled code 100%; overall type 98.6% (one LLM miss on the ICICI policy PDF).
- Classifier held-out accuracy: 90%.

Next, for the in-person round:
- Run against a real inbox (IMAP) and report real-inbox accuracy.
- Update the pitch deck (`~/Downloads/Personal_Admin_Brain_HackIIITD.pptx` is the old HackIIITD idea deck:
  rename to Sorted, swap "design targets" for real numbers, and reframe the MVP slide as built rather than
  planned).
- Docker `--network none` sandbox.
- TinyFish portal graduation (Agent → Browser/Playwright script → scheduled replay → fallback).
- Google Calendar events.
- Per-client MCP tokens.

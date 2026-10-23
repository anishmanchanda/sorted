# 07: Constants, thresholds and environment

## Tunables (defaults in code; env overrides where named)

| What | Value | Where / env |
|---|---|---|
| Accepted traces before a compile | 3 | `BRAIN_COMPILE_AFTER` (detector, questions, skills) |
| Held-out share | 0.3 (`round(n × 0.3)`, only when n ≥ 3; at least 1 visible) | `generator.HELD_OUT_SHARE` |
| Held-out pass rate to be `tested` | 0.98 | `generator.HELD_OUT_PASS` |
| Compile attempts | 2 (the second gets the failures) | `compile_ability` |
| Matching shadow runs before `active` | 2 (`make demo` / `make sim`: 1) | `BRAIN_SHADOW_RUNS` (`BRAIN_SIM_SHADOW_RUNS` for the sim) |
| Missed phrasings before a question recogniser is degraded | 2 | `query.MISSES_BEFORE_REPAIR` |
| Negative examples per question compile | ≤ 6, alternating visible/held-out | `query.compile_ability` |
| Classifier confidence for a local `ignore` | 0.7 | `BRAIN_CLASSIFIER_THRESHOLD` |
| Classifier rule layer | ≥ 2 examples per (sender_key, label) | `EmailClassifier.fit` |
| TF-IDF / LogReg | ngram (1, 2), sublinear_tf; C = 10, max_iter = 2000 | `classifier.py` |
| Sandbox | CPU 10 s, file size 1 MiB, timeout 15 s (10 s when run on a message or question) | `sandbox.py`, `registry.py`, `query.py` |
| Token budget per run / per day | 20 000 / 500 000 | `BRAIN_RUN_TOKEN_BUDGET`, `BRAIN_DAY_TOKEN_BUDGET` |
| OpenAI client retries | 3 | `LLM._client` |
| Quiet hours | 22–07 (wraps midnight) | `BRAIN_QUIET_HOURS` |
| Reminder merge window | 15 min | `scheduler.MERGE_WINDOW` |
| APScheduler | misfire_grace_time 3600, coalesce | `scheduler.get` |
| Days before due for relative reminders | bill 3, premium 3, renewal 7, meeting 1, at 09:00 | `planner.DAYS_BEFORE` |
| Meeting reminders | 1 day before at 09:00, and 1 hour before | `meetings.decide` |
| Skill reminder | 1 day before the due date | `skills.effects` |
| Due-date sanity window | received − 45 days … received + 400 days | `validate` |
| Duplicate/conflict window | ±7 days, same type, provider_match | `state.apply` |
| `upcoming` query window | 60 days | `query.window` |
| Chat context pack | obligations due ≤ 60 days ahead and ≥ −7 days | `agents.context_pack` |
| Digest list cap | 15 updates, then "…and N more" | `query.digest` |
| Generated messages per request | ≤ 12 | `Engine.generate` |
| Autopilot pace (s per event) | fast 0.8, normal 3.0, slow 5.0; ×3 after a chapter; half pace between auto-answers | `sim.SPEED` |
| Telegram send spacing | 0.7 s | `telegram_sim.sender` |
| Web auto-play / dashboard poll | 2.5 s / 3 s | `index.html` |
| Sim server port | 8000 | `BRAIN_SIM_PORT` |
| Telegram in the sim | on if a token is set | `BRAIN_SIM_TELEGRAM=0` turns it off |
| SMS webhook | 127.0.0.1:8787 | `brain serve-sms` |
| MCP over HTTP | 127.0.0.1:8765, path `/mcp` | `BRAIN_MCP_HOST`, `BRAIN_MCP_PORT` |
| Dataset RNG seed | 42 | `samples.py` |
| Canonical timeline end | 2026-09-30; months 4…9 = Sim months 1…6 | `samples.CANON_END` |

## `.env.example` (copy to `.env`; never commit `.env`)

```dotenv
OPENAI_API_KEY=
CEREBRAS_API_KEY=
TINYFISH_API_KEY=
TELEGRAM_BOT_TOKEN=
BRAIN_SMALL_PROVIDER=cerebras
BRAIN_SMALL_MODEL=gpt-oss-120b
BRAIN_STRONG_PROVIDER=openai
BRAIN_STRONG_MODEL=gpt-5.4
BRAIN_OPENAI_FALLBACK_MODEL=gpt-5.4-mini
BRAIN_CEREBRAS_FALLBACK_MODEL=gpt-oss-120b
# USD per 1M tokens (input/output). ESTIMATES: check your provider's pricing page.
BRAIN_PRICES=gpt-oss-120b=0.35/0.75,gpt-5.4=2.5/15,gpt-5.4-mini=0.75/4.5
BRAIN_LLM_CACHE=
BRAIN_RUN_TOKEN_BUDGET=20000
BRAIN_DAY_TOKEN_BUDGET=500000
BRAIN_COMPILE_AFTER=3
BRAIN_SHADOW_RUNS=2
BRAIN_CLASSIFIER_THRESHOLD=0.7
BRAIN_INGEST_TOKENS=            # name:token,name:token
IMAP_HOST=imap.gmail.com
IMAP_USER=
IMAP_PASSWORD=
BRAIN_MCP_TOKEN=
BRAIN_MCP_SCOPE=read-write      # or read
TELEGRAM_OWNER_ID=
BRAIN_QUIET_HOURS=22-07
# BRAIN_DB_URL=sqlite:///data/brain.db
TINYFISH_LIVE=0                 # 1 = real Agent runs (uses credits)
```

**Set by code, not by users:**
- `BRAIN_DB_URL`, `BRAIN_MODEL_DIR`, `BRAIN_ABILITIES_DIR` (demo/sim);
- `BRAIN_DATE_OFFSET` (days the timeline is shifted);
- `BRAIN_TODAY` (pins `config.today()` to the simulated date);
- `BRAIN_USER_NAME` (signs meeting replies);
- `BRAIN_SAMPLES_DIR`, `BRAIN_LABELS` (eval).

Relative paths in these are resolved against the repo root.

## Makefile targets

```make
setup:      uv sync; create .env from .env.example if missing; uv run brain init
dataset:    uv run python -m brain.samples
demo:       uv run python -m brain.demo
demo-live:  uv run python -m brain.demo --live
sim:        uv run python -m brain.web
test:       uv run pytest -q
lint:       uv run ruff check brain tests
eval:       (needs data/demo.db) BRAIN_DB_URL=sqlite:///data/demo.db uv run python -m brain.eval
train:      uv run python -m brain.ml.train
bot:        uv run python -m brain.telegram_bot
mcp:        uv run python -m brain.mcp_server
mcp-http:   uv run python -m brain.mcp_server --http
```

`uv run pytest abilities` runs the tests the compiler generated (the original build had 37).

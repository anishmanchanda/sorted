# 01: Architecture

## Repository layout

```
brain/
  __init__.py            (empty)
  config.py              env + paths; today() honours BRAIN_TODAY
  db.py                  SQLAlchemy models, engine, Session, init_db(), audit()
  messages.py            Message dataclass, IST, sender_key(), sim_sample(), from_eml(), html_to_text()
  redact.py              redact(text)
  filters.py             is_otp(text), looks_like_injection(text)
  validate.py            Extraction (Pydantic), TYPES, NEEDS_AMOUNT, validate(ext, received_at)
  state.py               apply(s, src, ext, problems) -> outcome; provider_match(a, b)
  llm.py                 LLM wrapper: routes, JSON + repair, budgets, cost, record/replay, date shift
  agents.py              InboxAgent, DocumentAgent, ChatAgent, EXTRACT_SYSTEM, CHAT_SYSTEM, context_pack
  planner.py             PlannerAgent (LLM once) + plan_obligations (relative reminders, no LLM)
  orchestrator.py        Orchestrator: ingest, process, drain, ask, ask_detail, free_chat
  scheduler.py           APScheduler wrapper: create_reminder, create_repeating, remind_before, fire_reminder
  notify.py              SINKS / ASK_SINKS; send_self(text), ask_self(text, actions)
  replies.py             rule-based replies: 1/done/taken, snooze N(m|h), paid [provider]
  rules/__init__.py      YAML rules engine; rules/*.yaml (3 rules)
  meetings.py            meeting-request flow: prompt, decide, parse_when, draft, followup, send, outbox
  actions.py             button actions (approve:/reject:/meet:/mail:/skill:)
  query.py               compiled chat questions: QuerySpec, answer_for, digest, answer, compile
  skills.py              new message categories -> skills
  score.py               privacy score per period; summary text
  eval.py                extraction accuracy per handler -> reports/eval.md
  samples.py             THE synthetic dataset generator (writes data/samples + data/eval/labels.jsonl)
  demo.py                `make demo`: non-interactive 6-month run -> reports/demo_run.md
  sim_env.py             use(): point a process at data/demo.db etc. BEFORE importing brain modules
  sim.py                 Engine: interactive simulation (clock, delivery, autopilot, months, generate)
  cli.py                 argparse CLI `brain`
  telegram_bot.py        the real-use bot (live DB); pure *_text functions for testability
  mcp_server.py          Brain MCP server (stdio + Streamable HTTP with bearer auth)
  compiler/
    __init__.py
    detector.py          groups traces -> candidates; subject_words(); ability_name()
    generator.py         compiler agent loop; split_cases; compare; export; HEADER; COMPILER_SYSTEM
    static_check.py      AST allowlist
    sandbox.py           subprocess runner
    registry.py          match / execute / shadow / activate / degrade / approve / listing
  ml/
    classifier.py        two-layer EmailClassifier; current(); threshold()
    train.py             labelled_examples, trace_examples, train, held_out_report
  sources/
    fixtures.py          load_fixtures(root) -> list[Message]
    imap.py              fetch(since, folder, limit)
    pdf.py               from_pdf(path, raw_path)
    sms_api.py           FastAPI app: POST /ingest/sms
    tinyfish.py          fetch / search / agent_run / portal
  web/
    __init__.py
    __main__.py          `python -m brain.web`: sim_env.use(), Engine(), uvicorn + Telegram front end
    server.py            create_app(engine, lifespan) -> FastAPI JSON API + serves index.html
    index.html           single-page dashboard (vanilla JS, no build step)
    telegram_sim.py      Telegram front end for the simulation
abilities/               compiled parsers exported by `make demo` (committed, for review)
data/
  samples/               committed synthetic dataset: email/*.eml, sms/sms.jsonl, pdf/*.pdf, dataset.json
  eval/labels.jsonl      ground-truth labels, one JSON per sample
  llm_cache/             committed record/replay cache (JSON per call)
  demo/ demo.db brain.db models/ telegram_owner   (git-ignored)
reports/                 demo_run.md, eval.md (written by make demo)
tests/                   60 offline tests + fixtures/tinyfish/agent_<hash>.json
docs/                    design.pdf, FEATURES.md, PROPOSAL_VS_BUILT.md, rebuild/
Makefile  pyproject.toml  .env.example  .gitignore  README.md  DEMO.md  CLAUDE.md
```

## The message pipeline (`Orchestrator.ingest`)

```
Message ──► is_otp(subject+body)? ──yes──► audit "dropped_otp", return {"outcome": "dropped_otp"}  (nothing stored)
   │no
   ▼
body_hash already stored? ──yes──► {"outcome": "already_seen"}
   │no
   ▼
store SourceRecord(text = message.redacted_text())          ◄── the ONLY text anything downstream sees
   ▼
process(s, src):
   _extract:
     looks_like_injection(text)? → Extraction(type="ignore"), handler "rule:injection_guard"
     ability = registry.match(s, src)                # highest-version active/shadow ability whose trigger matches
     ability active → registry.execute (sandbox) → ok: handler "ability:<name>@v<n>", 0 tokens
                                                 → fails: registry.degrade(...), continue to the LLM
     no ability → local classifier: confident "ignore" → handler "ml:<layer>", 0 tokens
     agent = InboxAgent (email) or DocumentAgent (sms/pdf/web)
     res = agent.extract(text, run_id, cache_key, known=skills.known(s))
     ability in shadow → registry.shadow(s, ability, src, res.data) (compare; the LLM result is the one used)
   problems = validate(ext, src.received_at)
   outcome = state.apply(s, src, ext, problems)
   rules.apply(...) unless problems → (fired, after_commit effects)
   outcome "open"     → after_commit += planner.plan_obligations(src.id)   (relative reminders)
   outcome "proposed" → after_commit += notify.ask_self(*meetings.prompt(src.id))
   type "other", no problems → after_commit += skills.effects(s, ext, src.id)
   add Trace(task_kind="extract", handler, tokens, cost, output_json=ext (exclude_none), accepted=not problems)
   src.status = "done"
commit ──► run every after_commit callable
```

- **Budget errors** (`BudgetExceeded`, `LLMUnavailable`, `openai.APIError`) inside `process` mark the source
  `queued` and return `{"outcome": "queued"}`. `Orchestrator.drain()` retries queued sources later.
- **Chat:** `Orchestrator.ask_detail(question)` → `query.answer(question, llm, fallback=self.free_chat)`.
  `free_chat` uses the ChatAgent with a typed-state context pack and records a `chat` trace.

## Processes

| Process | Entry | DB | Scheduler |
|---|---|---|---|
| CLI | `brain …` (`brain/cli.py`) | live `data/brain.db` | paused (schedules only) |
| Real-use Telegram bot | `make bot` → `python -m brain.telegram_bot` | live | **running** (fires reminders) |
| MCP server | `make mcp` (stdio) / `make mcp-http` | live | paused |
| SMS webhook | `brain serve-sms` (uvicorn 127.0.0.1:8787) | live | paused |
| Non-interactive demo | `make demo` → `python -m brain.demo` | `data/demo.db` | paused; jobs fired by a simulated clock loop |
| Interactive simulation | `make sim` → `python -m brain.web` (127.0.0.1:8000) | `data/demo.db` | paused; jobs fired by `Engine.advance` |

`make sim` and `make bot` share one Telegram token, so they cannot run at the same time.

## Layers and who may call whom

- `messages`, `redact`, `filters`, `validate`, `config`, `db` are leaves.
- `llm` uses `config`, `db` (day budget), `redact`.
- Agents use `llm`. `state` uses `db` and `validate`. `rules` uses `db`, `notify`, `scheduler`, `state`.
- The `compiler` package uses `db`, `llm`, `validate`, `state.provider_match`, `skills` (detector gating).
- The `orchestrator` uses agents, `compiler.registry`, `filters`, `meetings`, `notify`, `planner`, `rules`,
  `skills`, `state`, `ml.classifier`, and `query` (lazy import).
- `sim` uses everything. `web.server` and `web.telegram_sim` use `sim`.
- `notify` is the only way to reach the user. It has two sink lists that channels register into:
  - `SINKS`: `text -> None`;
  - `ASK_SINKS`: `(text, [(label, action_id)]) -> None`.

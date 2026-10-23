# 09: Build order, done-when, and the 60 tests

Build in this order. Each milestone ends with its tests passing (`make test`) and lint clean (`make lint`).
Write the tests with the milestone, not at the end.

## Test harness (write this first)

`tests/conftest.py`:
```python
import os
os.environ["BRAIN_DB_URL"] = "sqlite://"                 # in-memory, shared via StaticPool
os.environ["BRAIN_LLM_CACHE"] = ""                       # never replay the committed cache in tests
os.environ["BRAIN_MODEL_DIR"] = tempfile.mkdtemp(prefix="sorted-models-")
os.environ["BRAIN_ABILITIES_DIR"] = tempfile.mkdtemp(prefix="sorted-abilities-")
# ... then import brain modules

@pytest.fixture(autouse=True)
def fresh_db():                      # drop_all + init_db + classifier.set_current(None), before and after
class FakeLLM:                       # stands in for brain.llm.LLM
    def __init__(self, answer): self.answer, self.calls = answer, []
    def json(self, route, system, user, schema, run_id="", cache_key=None):   # MUST accept cache_key
        self.calls.append(user)
        return LLMResult(schema.model_validate(self.answer(user, schema)), 100, 0.0001, "fake")
@pytest.fixture
def make_llm(): return FakeLLM
@pytest.fixture(scope="session")
def fixtures(): return load_fixtures()          # the committed synthetic inbox
@pytest.fixture
def label_llm(fixtures):                         # a perfect extractor: returns the ground-truth label of the
    ...                                          # fixture whose redacted text is in the prompt (Extraction fields only)
```

**Patterns used throughout:**
- `monkeypatch.setattr(notify, "SINKS", [list.append])` to capture messages to the user;
- `scheduler.get().remove_all_jobs()` around scheduler tests;
- `monkeypatch.setattr(scheduler, "now", lambda: t)` for time;
- `monkeypatch.setenv("BRAIN_SHADOW_RUNS", "1")` and `monkeypatch.setenv("BRAIN_TODAY", …)`;
- hand-written parser code passed through a fake compiler (`schema.__name__ == "CodeGen"` → `{"code": PARSER}`);
- FastAPI's `TestClient`.

**Never** call a real provider, TinyFish or the network in a test.

## Milestones

### M0: Foundations
- **Build:** repo skeleton, `pyproject.toml`, Makefile, `.gitignore` (**first**), `.env.example`, `config.py`,
  `db.py`, `messages.py`, `redact.py`, `filters.py`, `validate.py`.
- **Dataset:** `samples.py` + the committed dataset + `labels.jsonl` (05), and `eval.py` (scoring).
- **Done when:** the dataset generates deterministically; redaction, OTP and injection filters pass; validation
  rules hold; every fact links to a source.
- **Tests:**
  - `test_privacy.py`:
    - `test_redaction_masks_identifiers_but_keeps_amounts_and_dates`: card → `XXXX XXXX XXXX 4821`, account
      `3000123456` → `XXXXXX3456`, two `[phone]`, `[email]`; `18,432.50`, `02/05/2026`, `526` and
      `20260415T103000` kept;
    - `test_redaction_is_idempotent`;
    - `test_otp_filter`: three OTP phrasings match; exactly the 4 OTP fixtures match; no other fixture matches;
    - `test_injection_detector`: only `data/samples/email/m3_injection.eml` is flagged.
  - `test_validate.py`: `test_valid_bill_passes`, and `test_rules`: amount 0, a blank provider, a missing due
    date on a premium and a 2030 due date each produce their message; a meeting with no amount and `ignore` are
    valid.
  - `test_db.py`: `test_fact_links_to_source`.
  - `test_eval.py`: `test_labels_cover_required_senders` (≥ 70 labels; covers the core types; has an injection
    sample and a `layout: v2` sample), `test_scoring` (provider_match, amount within 0.01, ignore scored on type only),
    `test_evaluate_groups_by_handler` (llm / compiled / rule / all).
  - `test_sim.py`: `test_generated_timeline_ends_on_the_given_date`, `test_sim_sample_and_score_periods` (ids →
    Sim month; real data → `YYYY-MM`).

### M1: LLM wrapper
- **Build:** `llm.py` (02 §6).
- **Done when:** routes and fallbacks work, there is one repair retry, prompts are redacted, cost and budgets are
  enforced, and record/replay works with date shifting.
- **Tests (`test_llm.py`):**
  - `test_routes_and_fallback`: a missing key → the other provider + its fallback model; no keys →
    `LLMUnavailable`;
  - `test_retry_once_with_validation_error_and_redaction`: a fake OpenAI client returns bad JSON then good; the
    second call includes the error; the user content sent is redacted;
  - `test_cost_and_budget`: price parsing and cost math; run budget → `BudgetExceeded`;
  - `test_record_and_replay`: a live call writes the cache file; a second LLM instance replays without a client.
- **Also:** `test_sim.py::test_replay_by_cache_key_moves_dates_with_the_timeline`.

### M2: Single-agent pipeline + state
- **Build:** `agents.py`, `state.py`, `orchestrator.py` (01 pipeline, without abilities yet), `sources/fixtures.py`,
  `sources/pdf.py`, CLI `init/ingest/ask/due/stats`.
- **Done when:** ingesting the whole dataset with a perfect extractor gives the right obligations, duplicates and
  conflicts; injection produces no action; agents have no dangerous tools; budget exhaustion queues and `drain`
  recovers; failed validation flags instead of dropping.
- **Tests (`test_orchestrator.py`):** `test_full_fixture_run_with_perfect_extractor`,
  `test_prompt_injection_email_produces_no_action`, `test_no_agent_can_send_pay_forward_or_delete` (every
  `TOOLS` tuple), `test_budget_exhaustion_queues_then_drains`, `test_failed_validation_flags_instead_of_dropping`.

### M3: Scheduler, rules, replies, planner, Telegram bot (real use)
- **Build:** `scheduler.py`, `notify.py`, `rules/` + 3 YAML rules, `replies.py`, `planner.py`, `telegram_bot.py`
  (pure `due_text`, `score_text`, `abilities_text`, `approve_text`, `audit_text`, `respond`; the handlers only
  wire them up).
- **Done when:** a 9 PM reminder fires with no LLM; quiet hours defer; nearby reminders merge; a relative reminder
  is created for a new bill; the medicine tracker logs doses and the refill alert fires at 5; `paid` and `snooze`
  work; a price-increase email updates state, schedules a reminder and alerts.
- **Tests:**
  - `test_m5.py`: `test_quiet_hours`, `test_reminders_due_close_together_are_merged`,
    `test_quiet_hours_defer_instead_of_sending`, `test_relative_reminder_for_new_obligation`,
    `test_medicine_tracker_dose_log_and_refill_rule`, `test_paid_and_snooze`, `test_due_text_and_routing`.
  - `test_rules.py`: `test_price_increase_rule_updates_state_reminds_and_alerts`,
    `test_no_alert_when_price_does_not_rise`, `test_condition_grammar`.

### M4: Ability compiler
- **Build:** `compiler/detector.py`, `generator.py`, `static_check.py`, `sandbox.py`, `registry.py`; wire the
  registry into the orchestrator; CLI `compile/approve/abilities`; export to `abilities/`.
- **Done when:** the full lifecycle works offline:
  - BSES traces → candidate → (fake compiler returns `PARSER_V1`) tested → approve → shadow → active (0 LLM
    calls);
  - a changed layout ("Net Amount Payable" → "Total Payable") → degraded + LLM fallback → v2 (`PARSER_V2`)
    tested;
  - a static-check failure feeds one retry;
  - the held-out split is 30% and deterministic;
  - malicious code is rejected; the sandbox has no network and no secrets, and times out.
- **Tests:**
  - `test_compiler.py`: `test_ability_lifecycle`, `test_static_check_failure_feeds_one_retry`,
    `test_held_out_split_is_30_percent_and_deterministic`.
  - `test_static_check_sandbox.py`: `test_static_check_accepts_clean_parser`,
    `test_static_check_rejects_malicious_sample` (os/socket/subprocess/pathlib imports, `open`, `eval`,
    `__import__`, dunder walks: all reported), `test_sandbox_runs_code_and_reports_errors`,
    `test_sandbox_timeout`, `test_sandbox_has_no_network_and_no_secrets` (sockets raise; env has no API keys).

### M5: Local ML classifier
- **Build:** `ml/classifier.py`, `ml/train.py`; the orchestrator consults it before the LLM; `make train`.
- **Done when:** the rule layer works for known senders and TF-IDF for unknown ones; held-out accuracy is
  reported; a confident `ignore` skips the LLM; unsure goes to the LLM.
- **Tests (`test_classifier.py`):** `test_rule_layer_for_known_sender_and_tfidf_for_unknown`,
  `test_held_out_accuracy_and_confident_predictions_are_reliable`, `test_confident_ignore_skips_llm_and_unsure_goes_to_llm`.

### M6: Channels: MCP server and SMS webhook; sources: IMAP, TinyFish
- **Build:** `mcp_server.py` (02 §15), `sources/sms_api.py`, `sources/imap.py`, `sources/tinyfish.py` + one
  recorded Agent fixture.
- **Done when:** the tools, resources and prompts are registered; read tools answer from state; write tools are
  scoped and audited; `run_ability` runs only active abilities; HTTP needs the bearer token; the SMS webhook
  rejects bad tokens, drops OTPs and ingests; TinyFish never goes live by default, replays the recorded run, stores
  it as a `portal` trace, and turns a bill result into an obligation.
- **Tests:**
  - `test_mcp.py`: `test_tools_resources_and_prompts_are_registered`, `test_read_tools`,
    `test_write_tools_are_logged_and_scoped`, `test_run_ability_only_runs_active_abilities`,
    `test_http_requires_bearer_token`.
  - `test_sms_api.py`: `test_sms_webhook_auth_otp_and_ingest`.
  - `test_tinyfish.py`: `test_not_configured_is_a_clear_message`, `test_agent_never_goes_live_by_default`,
    `test_recorded_agent_run_replays_and_is_stored_as_trace`, `test_bill_portal_result_becomes_an_obligation`,
    `test_fetch_message_flows_like_email`.

### M7: Privacy score + the non-interactive demo + eval reports
- **Build:** `score.py`, `demo.py`, `eval.py` report writing; record the LLM cache with real keys (`make demo`);
  write `reports/`; the README from those numbers.
- **Done when:** `make demo` runs end to end offline from the cache in seconds, and `reports/demo_run.md` shows
  the shape in 00/README: nothing local in Sim months 1–2, parsers compiled at the end of month 3, shadow in month
  4, the majority local in month 5, the HDFC v2 repair in month 6.

### M8: Meetings, compiled questions, new skills
- **Build:** `meetings.py`, `actions.py`, `query.py` (and route `Orchestrator.ask_detail` through it),
  `skills.py` (and the `other` type, the `category` field, `KNOWN CATEGORIES`, detector gating).
- **Done when:**
  - a meeting request asks with 3 buttons; "Another time" + "Friday 5pm" books the right slot with reminders,
    Meet and Calendar links and an .ics; nothing reaches the outbox until Send; Send is idempotent;
  - three questions of one intent compile a recogniser, which after approval and one shadow match answers with 0
    LLM calls, while other intents still go to the LLM;
  - "dues and updates between X and Y" returns a digest with normalised dates.
- **Tests (`test_interactive.py`):** `test_meeting_request_pick_another_time_then_reply_only_with_permission`,
  `test_dues_and_updates_between_two_dates`, `test_repeated_question_type_is_compiled_and_answered_without_llm`.

### M9: Interactive simulation, dashboard, Telegram front end, autopilot
- **Build:** `sim_env.py`, `sim.py`, `web/server.py`, `web/index.html`, `web/telegram_sim.py`, `web/__main__.py`,
  `make sim`; `DEMO.md`.
- **Done when:**
  - the engine and web API work: stepping a month delivers messages and fills stats; the dataset lists all 81;
    adding a message works; a bad step is a 400;
  - generated data arrives, Sorted proposes a skill after the 3rd message, nothing compiles until the user
    agrees, then the parser compiles, is approved, and the skill schedules its reminder;
  - the autopilot runs all six months unattended with 6 openings, 6 recaps and "🏁 Demo complete", books
    meetings, sends replies, leaves nothing pending, produces highlights, and `set_speed` changes the pace.
- **Tests (`test_interactive.py`):** `test_engine_and_web_api`,
  `test_generated_data_new_kind_of_message_becomes_a_skill`, `test_autopilot_runs_the_whole_demo_saying_yes`
  (with `engine.delay = 0`, and a FakeLLM that raises `LLMUnavailable` for `CodeGen` so compiles stay
  candidates).

**Total: 60 tests** (classifier 3, compiler 3, db 1, eval 3, interactive 6, llm 4, m5 7, mcp 5, orchestrator 5,
privacy 4, rules 3, sim 3, sms_api 1, static_check_sandbox 5, tinyfish 5, validate 2).

## Docs to write at the end
- **`README.md`** (judge-facing): pitch, results table copied from `reports/`, quickstart, interactive simulation,
  architecture, safety, built vs planned (honest), team.
- **`DEMO.md`:** a step-by-step demo guide (`/run`, the manual walkthrough, the Telegram command table).
- **`CLAUDE.md`:** a map and pitfalls for future sessions.
- **`docs/FEATURES.md`** and **`docs/PROPOSAL_VS_BUILT.md`.**

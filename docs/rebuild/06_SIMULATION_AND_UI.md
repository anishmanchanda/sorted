# 06: The demo, the interactive simulation, the dashboard and the Telegram front end

## 1. Two simulation entry points, one demo database

Both must point the process at `data/demo.db`, `data/demo/models` and an abilities directory **before importing
any `brain` module**: `config`, `db.engine` and `classifier.MODEL_PATH` read the environment at import time.

- **`brain/demo.py`** sets `os.environ` at the top of the module and then imports `brain`:
  - `BRAIN_DB_URL=sqlite:///data/demo.db`;
  - `BRAIN_MODEL_DIR=data/demo/models`;
  - `BRAIN_ABILITIES_DIR=<repo>/abilities` (committed, for reviewers);
  - `BRAIN_SHADOW_RUNS=1`;
  - `BRAIN_DATE_OFFSET=(END − CANON_END).days`, where END comes from `data/samples/dataset.json`.
- **`brain/sim_env.use()`**, called first by `python -m brain.web`, sets `BRAIN_DB_URL` (demo.db),
  `BRAIN_MODEL_DIR=data/demo/models`, `BRAIN_ABILITIES_DIR=data/demo/abilities`,
  `BRAIN_SHADOW_RUNS=${BRAIN_SIM_SHADOW_RUNS:-1}` and `BRAIN_USER_NAME=Rohan` (the persona signs meeting replies).

## 2. `make demo` (non-interactive, `brain/demo.py`)

1. **Set up:**
   - `LLM(cache_dir=data/llm_cache)`, or no cache with `--live` (`make demo-live`; it does not record);
   - print a markdown header (routes, compile-after, shadow runs);
   - delete `data/demo/sim.json` and `feed.jsonl`, so the interactive sim starts fresh;
   - drop and create all tables, remove all jobs, delete `abilities/` and the classifier model;
   - send `notify.SINKS` to a list, so alerts are printed under the message that caused them.
2. **For Sim month n = 1…6:**
   - **deliver** each sample of that month in time order, with `scheduler.now` patched to the message's
     `received_at`. Print one line per message (handler label, type, provider, amount, due, outcome), plus any
     `↳` notes: the ability event, `rule fired: X`, validation problems;
   - **move the clock** to `min(month_end(n), END at the current real time)`, where `month_end(n)` = the last day of
     canonical month n+3, shifted, at 23:59;
   - **fire the due reminders** (remove each job and print "⏰ … reminder fired by the scheduler (no LLM): …");
   - **compile:** `compile_pending(s, llm)`; print each result; auto-approve every `tested` one (actor `demo`) and
     say so;
   - **retrain:** `train(trace_examples())`;
   - **print the month's row** from `score.monthly`.
3. **Then:**
   - an abilities table;
   - the reminders still scheduled;
   - one TinyFish portal replay (the Netflix plan page, `PRICE_SCHEMA`);
   - the privacy table (`score.table`);
   - the extraction accuracy (`eval`);
   - one chat answer ("What do I need to pay in the next two weeks?"), skipped without a key;
   - `LLM calls this run: N live, M replayed`.
4. **Write** `reports/demo_run.md`; `brain.eval` writes `reports/eval.md`.

## 3. The interactive engine (`brain/sim.py: Engine(llm=None, data_dir=None)`)

**Construction:**
- `data_dir` defaults to `data/demo`; `llm` defaults to `LLM(cache_dir=data/llm_cache)`, so committed samples
  replay;
- it registers sinks that turn notifications into feed events: `notify.SINKS += emit("notify", text)` and
  `notify.ASK_SINKS += emit("ask", text, actions)`;
- **it sets `scheduler.now = self.now`**, so the whole process runs on simulated time;
- it loads `sim.json` and `feed.jsonl`, or calls `reset()`.

**State, `sim.json`:**
```json
{"end": "2026-10-23", "offset": 23, "month": 1, "delivered": ["m1_airtel", ...], "auto_approve": false,
 "clock": "2026-04-23T08:00:00", "final_tasks_done": false, "awaiting_time": 82}
```
`_env()` sets `BRAIN_DATE_OFFSET=offset` and `BRAIN_TODAY=clock date` after every clock change.

**Feed event** (in memory + appended to `feed.jsonl`; `emit()` also calls every function in `engine.listeners`,
swallowing their exceptions):
```json
{"id": 12, "sim_time": "2026-05-05T10:00", "sim_month": 2, "kind": "message", "title": "...", "detail": "...",
 "handler": "llm", "actions": [["✅ Approve", "approve:x"]], "label": "LLM", "sample": "m2_bses",
 "outcome": "open", "facts": "bill due · BSES Rajdhani · ₹959.00 · 20 May", "link": null, "meet": null}
```

**Event kinds:**

| Kind | Meaning |
|---|---|
| `message` | A message was delivered |
| `notify` | A reminder or alert to the user |
| `ask` | A question with buttons |
| `you` | The user's chat text |
| `chat` | An answer; `detail` = `how()` text |
| `action` | A button press; `detail` = the action id, `handler` = `you` / `auto-approve` / `autopilot` |
| `compile` | A compile result |
| `system` | Other notices |
| `outbox` | A reply was sent |
| `chapter` | A month opening or recap (with `month`) |

**Clock and months:**
- `month_end(n)` = `date(2026, n+3, last day) + offset` at 23:59; `month_of(t)` = the first n with `t ≤
  month_end(n)`, else 6.
- `month_range(n)` = (`date(2026, n+3, 1) + offset`, `month_end(n).date()`).
- `end()` = `state.end` at 23:59.

**`reset()`:**
- drop and create the tables, remove all jobs, delete the sim abilities dir, the classifier and the feed;
- keep `auto_approve`;
- state: `end` = `dataset_end()`, extended by `_extend_end()` to the latest added message;
- clock = the day before the first message at 08:00;
- emit "Simulation reset", then, unless the autopilot is running, the chapter "📅 Sim month 1 begins · d Mon –
  d Mon" with the narration.

**Messages:** `messages()` = `load_fixtures(SAMPLES_DIR)` + `load_fixtures(data/demo/extra)` (when it exists),
sorted.

**`add_message(kind, sender, subject, body, at=now+1min, label="your message", quiet=False)`:**
- writes `extra/email/<sid>.eml` (or a line in `extra/sms/sms.jsonl`) and `extra/labels.jsonl` (`{id, type:
  label}`);
- `sid` = `{sms_}m{month_of(at)}_user{n}`.

**`advance(until)`** (under `self.lock`, an RLock):
- `until = min(until, end())`; `pending` = undelivered messages with `received_at ≤ until`;
- loop:
  - take the earliest of the next due job and the next pending message;
  - stop when it's past `until`;
  - **close every Sim month whose end is before it:** `_close_month()` = `_month_tasks(n)`, then `state.month =
    n+1`, then `_chapter_begin(n+1)`. Month tasks run while the clock is still inside month n, so their events
    belong to month n;
  - **set the clock** to `max(clock, t)`, then `_env()`;
  - **fire the job, or deliver the message.** Jobs win ties.
    - Date jobs are removed and run: FIRE jobs through `scheduler.fire_reminder(**kwargs)`, others through
      `job.func(**kwargs)`.
    - Cron jobs are run, then moved to their next fire time.
    - Delivered messages are added to `state.delivered`.
  - save;
- after the loop, close any remaining months before `until`, set the clock to `until`;
- if `until ≥ end()` and the final tasks haven't run, run `_month_tasks(6)` once (`final_tasks_done`);
- return the new feed events.

**`step(to)`:**
- `next`: advance to the earliest pending message or job;
- `day`, `week`: now + 1 day / 7 days;
- `month`: to the end of the current Sim month, or the next one if already at the end;
- `end`: to `end()`.

**`_deliver(m)`:**
- run `orch.ingest`;
- **label:** "dropped before storage" for OTPs; "compiled code" for `ability:`; "local ML" for `ml:`; "rule" for
  `rule:`; "LLM" for `llm`;
- **facts:** `type · provider · ₹amount · dd Mon`, or `query.facts(...)` for `other`;
- emit a `message` event, then `_reassess()`.

**`_reassess()`:** `skills.scan` + `plan` for each new skill. Emit "Re-assessing: a new kind of message keeps
arriving (<cat>)". With auto-approve, `act("skill:<cat>:yes", by="auto-approve")`; otherwise `ask_self(prompt)`.

**`_month_tasks(n)`:**
- compile `compile_pending(s, llm)` + `query.compile_pending(s, llm)` and retrain the classifier;
- `_report_compile` each result. **Tested results** are auto-approved when `auto_approve` is on (emit
  "Auto-approved for the demo: …"); otherwise `ask_self(actions.approval_prompt(r))`;
- emit "End of Sim month n", then the chapter "📊 Sim month n recap" with `recap(months()[n-1])`.

**`ask(text)`:**
1. emit `you`;
2. **if a meeting time is awaited** and the text looks like a time: `meetings.parse_when`. Not parseable → "I
   couldn't read a future time from that. Try "Friday 5pm" or "14 Jun 11:30"." Otherwise `act("meet:<id>:at:<iso>")`
   and answer with its text, `how = "📏 time parser · no AI"`;
3. otherwise clear `awaiting_time` and try, in order:
   - `replies.handle`;
   - the planner, if `PLAN_HINT` matches and it returns text;
   - `orch.ask_detail`;
4. set `out["how"] = how(handler, event)` and emit `chat`;
5. if `query.scan` finds candidates, start a background thread that takes the lock, emits "You keep asking this
   kind of question: compiling it into code…", compiles and reports.

**`how(handler, event)`** (shared with Telegram):
- the tag is "⚡ compiled code · 0 AI calls" (ability), "📏 rule · no AI" (rule), or "🧠 AI" (llm);
- in the event, `ability:x@vN` is rewritten as `x vN`, and the phrases are made readable ("agreed with the AI, so
  code answers from now on", "disagreed with the AI, so it will be recompiled", "so the AI answered (code will
  learn it)");
- the result is the tag, plus " · <event>" unless the event is the default one.

**`act(action, by="you")`:**
- `actions.handle`, then emit `action` (with `link`/`meet`);
- set or clear `awaiting_time`;
- for `sent`, emit `outbox` with the mail body;
- for `followup`, `notify.ask_self(*followup)`;
- for `compile`, a background thread runs `compile_pending(only_type=category)` and reports; with no candidates,
  it emits "Skill active; no code to compile yet".

**`generate(request)`:**
- one small-route call with `GEN_SYSTEM` (03 §9). The user turn includes the timeline (the day before the first
  message at 08:00 … end) and the current clock;
- emit "Generated N synthetic messages: <label>";
- `add_message(..., quiet=True)` each (at most 12), clamped to the timeline start; ASCII-translate the
  subject/body;
- extend the end and save;
- if any are dated at or before now, emit "Backfilling …" and `advance(now)`, delivering them immediately in
  order;
- return `{label, ids, backfilled, later, tokens}`, or `{error}` without a key.

`clear_added()` deletes `data/demo/extra`.

**`status()`:**
```
{clock, month, end, delivered, total, auto_approve, awaiting_time, pending_actions, autopilot, feed_len, speed}
```
`pending_actions` = `ask` events none of whose action ids has been acted on. Ids ending `:other` don't count as
answers; a `meet:<id>:at:` action answers `meet:<id>:yes`.

**Other views:**
- `stats()`: `{months: score.monthly, messages, local, privacy, llm_calls, tokens, cost, questions: {llm, local}}`.
- `abilities()`: per ability its lineage, i.e. `llm_solves` (the group size), `local_runs` (traces with its
  handler), compile info and tokens, the audit history, code and tests.
- `dataset()`: every message with `{id, sim_month, time, kind, sender, subject, label, added, status}`.
- `message(sid)`: the raw and redacted text plus the last feed event for it.

**`months()`, one dict per Sim month:**
```
{n, label, start, end, narration, status: done|now|upcoming, messages, local, llm_calls, privacy,
 compiled: ["name vN" with "-> tested"], failed: ["name vN" compiled but not tested],
 took_over: [from "ability:x@vN shadow match k/N -> active" in message details, and "x vN agreed with the AI" in chat],
 broke: [from "ability:x@vN failed"], skills: [labels of skills accepted that month],
 meetings: count of "✅ Booked" actions, replies: outbox events, reminders: notify events,
 questions_by_code: chat events with an ability handler, highlights: [plain-language lines]}
```
- **`ability_labels(s)`** names abilities for people: parsers as "<last provider seen> <type words> emails|SMS"
  (`bill due` → `bill`, `receipt` dropped); questions as "<intent> questions"; skills as "<title> (<action
  text>)".
- **`highlights()` order:**
  - 💥 broke ("… changed layout: the code broke and the AI took over again");
  - ⚙️ "Learned to read|answer X: code written and tested" (v1), or 🔧 "Rewrote the code for X to match the new
    layout (vN)";
  - ✅ "X now handled by code, not the AI";
  - ⏳ "Not yet: code for X failed its tests; the AI keeps the job";
  - 🆕 "Noticed a new kind of message and learned a skill for it: …".
- **`recap(m)`:** "N messages: L by compiled code, A by the AI · privacy P%", then "Highlights:" and the lines
  (or "No new skills this month."), then "R reminders · M meetings booked · S replies sent · Q questions answered
  by code".
- **`learned()`:** every ability with the month its code was written and the month it took over.

**Narration per Sim month** (`NARRATION`):
1. "The AI reads every message. Reminders are scheduled from what it extracts and fire with no AI."
2. "The same senders write again. Every AI answer is saved as a trace: examples for the compiler."
3. "At the end of this month the compiler writes code for each sender seen 3 times, and tests it."
4. "Shadow month: the new code runs next to the AI and must agree with it before it takes over."
5. "Compiled code now reads the repeat senders: no AI call, nothing leaves the machine."
6. "HDFC changes its email layout: watch its parser fail, fall back to the AI, and v2 get compiled."

## 4. Autopilot (`/run`, ▶ Run full demo)

- `start_autopilot(speed="normal", generate=True)` starts a daemon thread, unless one is already running. `SPEED
  = {fast: 0.8, normal: 3.0, slow: 5.0}` seconds per event, stored in `engine.delay` and **read on every
  event**, so `set_speed()` changes a running demo.
- `stop_autopilot(wait=False)` sets an Event; every wait is `self._stop.wait(seconds)`.
- **`_autopilot(generate)`:**
  1. `reset()`, `set_auto_approve(True)`, then the chapter "▶ Full demo on autopilot";
  2. if `generate`: `generate("a business sending in requests for new shipments sporadically over the months")`.
     An error emits "Skipped the generated data";
  3. the chapter "Sim month 1 begins";
  4. **loop until stopped or the clock reaches the end:**
     - `step("next")`;
     - `_auto_answer(delay/2)`;
     - ask at most one scripted question per step, for the current Sim month, each only once;
     - wait `delay × 3` if a chapter was emitted in this step, else `delay`;
  5. when it finishes: answer the remaining asks, then the chapter "🏁 Demo complete" with the totals.
- **`_auto_answer`:** while asks are pending (at most 20), choose the first action ending `:yes`/`:send` or
  starting `approve:` (else the first), `act(choice, by="autopilot")`, then wait.
- **Scripted questions:**
  - month 2: "Do I have any doctor appointments this month?";
  - month 3: "Any appointments coming up?", "When is my next doctor appointment?" (the third question of one
    intent → it compiles);
  - month 4: "Any doctor appointments this month?" (shadow);
  - month 5: "Do I have a doctor appointment next month?" (compiled code);
  - month 6: "Give me all my dues and updates between {start of Sim month 4} and {end of Sim month 5}".
- **Manual steps** from the web or Telegram pause the autopilot first (`stop_autopilot(wait=True)`).

## 5. Web server (`brain/web/server.py: create_app(engine, lifespan=None)`)

Endpoints are sync (FastAPI runs them in a thread pool); the engine serialises with its lock.

| Method + path | Body / query | Returns |
|---|---|---|
| GET `/` | | `index.html` (read from disk on every request) |
| GET `/api/state` | | `{status, stats}` |
| GET `/api/feed?after=<id>` | | events with id > after |
| GET `/api/abilities` | | `engine.abilities()` |
| GET `/api/messages` | | `engine.dataset()` |
| GET `/api/messages/{sid}` | | `engine.message(sid)` or 404 |
| POST `/api/messages` | `{kind="email", sender, subject="", body, at?}` | `{id}` |
| DELETE `/api/messages/added` | | `{removed}` |
| POST `/api/generate` | `{request}` (400 if blank) | `engine.generate()` |
| GET `/api/months` | | `engine.months()` |
| GET `/api/learned` | | `engine.learned()` |
| POST `/api/run` | `{speed="normal", generate=true}` | `{started}` |
| POST `/api/speed` | `{speed}` | `{speed}` |
| POST `/api/stop` | | `{stopping: true}` |
| POST `/api/step` | `{to: next\|day\|week\|month\|end}` (else 400) | `{events}`; pauses the autopilot first |
| POST `/api/settings` | `{auto_approve}` | echo |
| POST `/api/reset` | | `{ok: true}` |
| POST `/api/chat` | `{text}` | `engine.ask()` |
| POST `/api/action` | `{action}` | `engine.act()` minus `ics`, plus `ics_url` `/api/ics/<source_id>` when booked |
| GET `/api/ics/{source_id}` | | a `text/calendar` attachment |
| GET `/api/outbox` | | `meetings.outbox()` |

**`brain/web/__main__.py`:**
- `sim_env.use()`, then `Engine()`;
- a lifespan that starts `telegram_sim.start(engine, token)` when `TELEGRAM_BOT_TOKEN` is set and
  `BRAIN_SIM_TELEGRAM != "0"`, and stops it on shutdown;
- `uvicorn.run(app, host="127.0.0.1", port=BRAIN_SIM_PORT or 8000)`.

## 6. The dashboard (`brain/web/index.html`, one file, vanilla JS, no build)

- **Design tokens:** CSS variables with light and dark (`prefers-color-scheme`). The colours are: the LLM in
  orange, compiled code in green, ML in purple, and the accent in blue.
- **`.hidden{display:none}` caution:** an ID rule with `display:flex` beats the `.hidden` class, so add an
  explicit `#modal.hidden{display:none}`. Without it an invisible overlay greys out the page and eats every
  click.
- **Header:**
  - the clock and a "Sim month n/6" pill (shows "· autopilot" while running);
  - buttons: Next event, +1 day, +1 week, To month end, Run to today, auto-play, auto-approve, Reset;
  - a pace select (fast/normal/slow → POST /api/speed), **▶ Run full demo** (asks to confirm), ⏩ Faster (while
    running and not already fast), ■ Stop.
- **Overview tab:**
  1. **Month by month:** a horizontal strip of 6 cards. Each card shows the status pill, the date range, a big %,
     a code/AI split bar, "N messages: L code · A AI · C AI calls", the narration, the highlights and the extras.
     The current month has an accent outline and is scrolled into view when the month changes.
  2. **Skills learned so far:** a table of what, kind, code written (Sim month), took over (Sim month), and now
     (doing the work / shadowing the AI / broke, replaced / awaiting approval / declined).
  3. **Privacy:** tiles (privacy score, LLM calls + tokens + cost, questions by code, cost per message); per-month
     stacked bars (green code, orange AI) labelled "L code · A AI"; a month table.
  4. **"From AI to compiled code":** ability cards.
     - **Pipeline:** LLM solves → tests shown + held-out (pass %) → approved → shadow k → N local runs.
     - **Details:** an offload bar, the last error, Approve/Reject while `tested`, and a collapsible "code the AI
       wrote · N test cases" (code + case table, with held-out pills).
     - **Skill cards** are distinct: proposed/learned/declined, and Learn it / Not now.
- **Synthetic inbox tab:**
  - an "Add a synthetic message" form, with templates for a meeting request, a bill and a doctor appointment;
  - a table of every message (click to open a modal with the redacted text and how it was handled; an "added"
    pill marks your own);
  - "Remove messages I added".
- **Aside:**
  - **Ask Sorted:** a chat box showing `how` above the answer, with link buttons (🎥 Google Meet, 📅 Add to Google
    Calendar, .ics);
  - **Waiting for you:** the pending asks with buttons, disabled after a click; "Another time" focuses the chat
    box;
  - **Add synthetic data:** a textarea + Generate;
  - **Outbox;**
  - **Live feed:** newest first; chapter events as banners.
- **Polling:**
  - `refresh()` every 3 s (state, months, learned, outbox, feed since the last id);
  - when `status.feed_len < lastFeed` (a reset from Telegram), clear the feed and start over;
  - abilities reload when new events arrive;
  - auto-play steps "next" every 2.5 s.

## 7. Telegram front end for the simulation (`brain/web/telegram_sim.py`)

`start(engine, token)` builds a python-telegram-bot `Application`, registers the handlers, starts polling, and
starts **one sender task** that drains an `asyncio.Queue`. Every message from any thread goes through
`send(text, markup, parse_mode)` → `loop.call_soon_threadsafe(queue.put_nowait, …)`. The sender sends in order,
sleeping 0.7 s between messages: no bursts, no reordering. `stop(app)` cancels the sender task and shuts down.

**Owner:** the same as the real bot (`data/telegram_owner` or `TELEGRAM_OWNER_ID`; the first `/start` claims
it).

**Commands:**

| Command | Does |
|---|---|
| `/start`, `/help` | HTML help |
| `/run [fast\|normal\|slow] [nodata]` | Start the autopilot; the default pace is the current one |
| `/fast`, `/normal`, `/slow` | Change the pace, also mid-run |
| `/stop` | Pause the autopilot |
| `/next`, `/day`, `/week`, `/month`, `/end` | Step by hand. The autopilot pauses first ("⏸ Autopilot paused…"). Reply with a summary, then each chapter event (opening, recap) as its own message |
| `/sim` | The clock and progress |
| `/score` | The privacy table in `<pre>` |
| `/due` | Due this week (no AI) |
| `/abilities` | What has been compiled |
| `/reset` | Start over |
| `/generate <description>` | `engine.generate` |
| Text | `engine.ask`; the reply is the answer + an italic `how` line + link buttons |
| A button press | `engine.act(data)`; edit the message to append "→ result" and remove the buttons (ignore `BadRequest` for a double press); send the `.ics` as a document when booked |

- **Step summary** (HTML): "⏩ **Thu 4 Jun 2026, 09:00** · Sim month 2/6", "N new messages: L by local code, A by
  the AI", then up to 8 lines of `📧/💬/📄 **sender** · 🧠 AI|⚡ code|🤖 local ML|📏 rule|🗑 OTP, dropped` with the
  facts indented beneath.
- **Notifications outside autopilot:** `notify` sinks send the text; asks get inline buttons (one row for ≤ 2
  buttons, else one per row).
- **During autopilot,** those sinks are muted and a **narrator** listener on `engine.listeners` sends one paced
  message per interesting event:

  | Event | Telegram message |
  |---|---|
  | chapter | bold title + detail |
  | message | `<i>MM-DD</i>` + the step line |
  | notify | "🔔 …" |
  | ask | "❓ …" (no buttons) |
  | autopilot/auto-approve actions, except `mail:` | "🤖 **Auto-yes** · …" with Meet/Calendar URL buttons |
  | outbox | "📤 **Reply sent** (outbox, simulated)" + subject + body |
  | compile | "⚙️ …" |
  | you / chat | "🙋 *You ask:* …" / the answer + `how` |
  | selected system events | "ℹ️ …" |

- **Replies retry once** on a `NetworkError` (Telegram times out sometimes).

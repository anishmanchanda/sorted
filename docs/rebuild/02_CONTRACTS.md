# 02: Data model, schemas and interfaces

Everything here is a contract: other modules, the tests and the prompts depend on these exact names.

## 1. `Message` (`brain/messages.py`): the one internal format

```python
@dataclass
class Message:
    kind: str          # email / sms / pdf / chat / web
    sender: str        # email: "Name <addr>"; sms: header like "VM-HDFCBK"; pdf: "upload"
    subject: str
    body: str
    received_at: datetime   # naive, IST
    raw_path: str = ""      # where the raw lives; also identifies samples (see sim_sample)
```

- `body_hash` = sha256 of `f"{kind}|{sender}|{subject}|{body}"`. It is unique in `source_records`, which makes
  ingestion idempotent.
- `sender_key(kind, sender)` is the grouping key:
  - email → the lower-cased domain of the address;
  - sms → the header without the operator prefix (`VM-HDFCBK` → `HDFCBK`);
  - otherwise → `kind`.
- `redacted_text()` is exactly this, and is the ONLY text agents, abilities and the compiler see:
  ```
  From: {sender}\nSubject: {redact(subject)}\nDate: {received_at:%Y-%m-%d %H:%M}\n\n{redact(body.strip())}\n
  ```
- **`from_eml(bytes, raw_path)`:**
  - prefers the HTML part, converted to text by `html_to_text` (block tags → newlines, `td/th/span` → spaces,
    `script/style` skipped, runs of whitespace collapsed, at most 2 blank lines);
  - appends `text/calendar` attachments as `\n\n[attachment <name>]\n<ics>` and PDF attachments as extracted text;
  - takes `received_at` from the `Date` header, converted to naive IST.
- `sim_sample(raw_path)` uses regex `(?:^|[/#])((?:sms_)?m(\d+)_[\w-]+?)(?:\.(?:eml|pdf))?$` and returns
  `(sample_id, sim_month)` or None.
- **`raw_path` conventions:**
  - email: `data/samples/email/<id>.eml`;
  - SMS: `data/samples/sms/sms.jsonl#<id>`;
  - PDF: `data/samples/pdf/<id>.pdf`;
  - SMS webhook: `sms:webhook:<user>`;
  - paths are relative to the repo root when inside it.
- `load_fixtures(root)`: every `email/*.eml`, every line of `sms/sms.jsonl` (`{id, sender, received_at ISO,
  body}`), and every `pdf/*.pdf`, sorted by `received_at`.
- `from_pdf(path, raw_path="", received_at=None)`: `kind="pdf"`, `sender="upload"`, subject = the file name
  (`Path.name`), body = pdfplumber text of every page joined by newlines, `received_at` = the metadata
  `CreationDate` parsed as `D:YYYYMMDDHHmmSS` (falling back to the file's mtime). The sample PDFs set
  `creation_date` deliberately.

## 2. `Extraction` (`brain/validate.py`): the output of every extractor, LLM or compiled

```python
EmailType = Literal["bill_due", "premium_due", "insurance_renewal", "subscription_receipt",
                    "subscription_price_change", "meeting", "meeting_request", "document_expiry", "other", "ignore"]
NEEDS_AMOUNT = {"bill_due", "premium_due", "insurance_renewal", "subscription_receipt", "subscription_price_change"}

class Extraction(BaseModel):
    type: EmailType
    provider: str | None = None
    amount: float | None = None      # bill total / premium / charged price / new price
    currency: str = "INR"
    due_date: date | None = None     # due / expiry / next billing / effective / appointment date
    service: str | None = None       # subscriptions (the brand)
    old_price: float | None = None
    new_price: float | None = None
    event_time: str | None = None    # "HH:MM" for meetings
    person: str | None = None
    topic: str | None = None         # meeting requests and `other`: what it is about
    document_type: str | None = None
    category: str | None = None      # `other` only: snake_case label for a new kind of message
```

The field order above is `FIELD_ORDER` for the compiler.

`validate(ext, received_at) -> list[str]` returns its problems; an empty list means valid. `ignore` is always
valid. Otherwise:
- `provider` must be non-blank → "provider is empty";
- types in `NEEDS_AMOUNT` need `amount > 0` → "amount must be > 0";
- `subscription_price_change` needs `new_price > 0`;
- `other` needs `category` matching `[a-z][a-z0-9_]{2,39}` → "category must be a snake_case label";
- `due_date` is required except for `other` → "due_date missing";
- when present, `due_date` must be within `[received - 45 days, received + 400 days]` →
  "due_date X outside A..B".

## 3. Database (`brain/db.py`, SQLite via SQLAlchemy 2.0, `Session = sessionmaker(engine, expire_on_commit=False)`)

- **Engine:** `BRAIN_DB_URL` (default `sqlite:///data/brain.db`). When the URL is `sqlite://` (tests), use
  `StaticPool` + `check_same_thread=False`, so every thread shares one in-memory DB.
- **Scheduler jobs** live in APScheduler's own `apscheduler_jobs` table in the same DB.

| Table | Columns (type, default) |
|---|---|
| `source_records` | id; kind str(10); sender str(255) ""; subject str(500) ""; **body_hash str(64) unique**; received_at datetime; raw_path str(500) ""; **text** (redacted) ""; status str(10) "new" (new/done/queued) |
| `obligations` | id; type str(40) (bill/premium/renewal/subscription/meeting/<category>); provider str(120); amount numeric(12,2)?; currency "INR"; due_date date?; repeat_rule str(60) "" ("monthly"); status str(20) "open" (open/paid/flagged/proposed/declined); confidence float 1.0; note text ""; source_id → source_records |
| `subscriptions` | id; **service unique**; price numeric; effective_date?; source_id |
| `medications` | id; name; dose str(60); times str(60) (comma-separated HH:MM); stock int; person "me"; source_id |
| `dose_log` | id; medication_id; taken_at default now |
| `documents` | id; type str(60) (puc/insurance_policy/…); expiry date?; source_id |
| `traces` | id; run_id str(40); task_kind str(40) (extract/chat/compile/query/plan/plan_skill/portal); input_ref → source_records?; output_json JSON; handler str(80) ("llm", "ability:<name>@v<n>", "ml:<layer>", "rule:<name>"); tokens int; cost float (USD est.); accepted bool; created_at |
| `abilities` | id; name; kind (parser/query/skill); trigger_json JSON; code text; version int; status (candidate/generated/tested/shadow/active/degraded/retired); permissions JSON list; runs; failures; shadow_matches; repair_from_source int?; last_error text; created_at. **Unique (name, version)** |
| `ability_tests` | id; ability_id; input text; expected_output JSON; held_out bool |
| `audit_log` | id; at default now; actor str(60); action str(60); detail JSON |

`audit(session, actor, action, **detail)` adds an `AuditLog` row; the caller commits.

## 4. State semantics (`brain/state.py`)

`apply(s, src, ext, problems) -> outcome`:
- `ignore` → `"ignored"` (nothing stored).
- `subscription_price_change` → `"price_change"`. Only the rules engine acts on it.
- `document_expiry` → adds a `Document(type=document_type or "document", expiry=due_date)` → `"document"`.
- `subscription_receipt` without problems: upsert `Subscription(service = provider or service)` with
  `price = amount`. A receipt is what was charged, so it is the current price. Then continue as an obligation.
- **Otherwise an `Obligation` is created:**
  - **type:** `OBLIGATION_TYPE[ext.type]`, i.e. bill_due→bill, premium_due→premium, insurance_renewal→renewal,
    subscription_receipt→subscription, meeting/meeting_request→meeting. For `other` the type is `ext.category`.
  - **repeat_rule:** `"monthly"` for bill/premium/subscription receipts.
  - **status:** `flagged` when there are problems, else `proposed` for `meeting_request`, else `open`.
  - **confidence:** 0.4 when flagged.
  - **note:** for meetings, `"HH:MM · person · topic"` (the parts that exist, joined by ` · `); for `other`, the
    topic. Problems are appended with `; `.
  - **Duplicates and conflicts** (skipped for `other`): look at obligations of the same type with a due date within
    ±7 days whose provider matches.
    - Same amount (or both None) and the same due date → audit `duplicate`, return `"duplicate"` (nothing added).
    - Otherwise both rows become `flagged`, the new one at confidence ≤ 0.5, and both notes say
      `conflicts with obligation #id` / `conflicting fact from source #id`; audit `conflict`.
  - Return the new obligation's status.
- **`provider_match(a, b)`:** lower-case alphanumeric token sets. True if either sorted-token string contains the
  other, or if the sets share a token outside the stop set `{bank, ltd, limited, india, of, the, co, company,
  insurance, power, govt, premium, plan, standard, individual, subscription, membership, service, services}`.
  Both None → equal.

## 5. Filters and redaction (verbatim)

```python
# filters.py
_OTP = re.compile(r"\b(?:otp|one[\s-]?time[\s-]?password|verification code|security code)\b\W+(?:\S+\s+){0,10}?\d{4,8}\b"
                  r"|\b\d{4,8}\b\W+(?:\S+\s+){0,3}?(?:otp|verification code)\b", re.I)
_INJECTION = re.compile(r"ignore (?:all |any )?(?:previous|prior|above|earlier) instructions"
                        r"|disregard (?:all |any )?(?:previous|prior|the above)"
                        r"|you are now (?:in )?\w+ mode|system prompt"
                        r"|forward (?:all|every|this) (?:mail|email|message)", re.I)
# redact.py, applied in this order
_EMAIL   = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"                    -> "[email]"
_CARD    = r"\b(?:\d[ -]?){12,18}\d\b"                        -> "XXXX XXXX XXXX " + last 4 digits
_PHONE   = r"(?<![\d.,])(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d|[.,]\d)"   -> "[phone]"
_ACCOUNT = r"(?<![\d/.,])\d{9,18}(?!\d|[/.,]\d)"              -> "X" * (len-4) + last 4
```

Redaction must be idempotent and must keep amounts and dates (tested).

## 6. LLM wrapper (`brain/llm.py`)

- `LLM(cache_dir=None)`: the cache directory is `cache_dir` or env `BRAIN_LLM_CACHE` (empty = no cache).
- **Routes:**
  - `route("small"|"strong") -> (provider, model)`, from `BRAIN_{ROUTE}_PROVIDER` (default cerebras/openai) and
    `BRAIN_{ROUTE}_MODEL`.
  - If the provider's `{PROVIDER}_API_KEY` is missing, switch to the other provider with
    `BRAIN_{OTHER}_FALLBACK_MODEL`.
  - No keys at all → `LLMUnavailable`.
- **Clients:** `OpenAI(api_key, base_url, max_retries=3)`, with base_url None for openai and
  `https://api.cerebras.ai/v1` for cerebras.
- **`json(route, system, user, schema, run_id="", cache_key=None) -> LLMResult(data, tokens, cost, model,
  replayed)`:**
  1. `user = redact(user)`.
  2. **Cache key:** sha256 of `json.dumps([route, system, schema.__name__, cache_key])` when `cache_key` is given,
     else of `[route, system, user, schema.__name__]`.
  3. **Cache hit:** the file `<cache_dir>/<key>.json` holds `{data, tokens, cost, model, date_offset, key}`. On a
     hit with a cache_key, every ISO date or datetime string in `data` is shifted by
     `BRAIN_DATE_OFFSET - recorded date_offset` days.
  4. **Budgets:** `run_tokens[run_id] >= BRAIN_RUN_TOKEN_BUDGET` (20000) or today's summed `traces.tokens >=
     BRAIN_DAY_TOKEN_BUDGET` (500000) → `BudgetExceeded`.
  5. **Call:** `chat.completions.create(model, messages=[system, user], response_format={"type": "json_object"})`.
     Validate with `schema.model_validate_json`; on a `ValidationError`, one repair turn (see 03_PROMPTS §10); a
     second failure raises.
  6. **Cost** = `(prompt_tokens * in + completion_tokens * out) / 1e6`, using `BRAIN_PRICES`
     (`model=in/out,...`, USD per 1M tokens).
  7. **Record:** on a live call with a cache dir, write the cache file.
- `stats` Counter: `live`, `replayed`.

## 7. Abilities: file format, sandbox protocol, comparison

**A parser ability's code** = `HEADER` (03_PROMPTS §5) + the model's code. The module defines
`extract(text: str) -> dict` and raises `ValueError` when its labels are missing (layout changed). It sees the
redacted text described in §1.

**Trigger:**
- parsers: `{"kind": "email"|"sms"|..., "sender_key": "hdfcbank.net", "type": "bill_due", "subject_keywords":
  [≤6 words common to every example's subject, email only], "n_traces": N}`;
- questions: `{"kind": "query", "intent": ...}`;
- skills: `{"kind": "skill", "category": ..., "plan": {...}, "n_traces", "senders"}`.

`kind` never equals a source kind for questions and skills, so they never match a message.

**Names:**
- parsers: `{"sms_" if sms}{sender_key with non-alphanumerics → "_"}_{type}` (e.g. `hdfcbank_net_bill_due`,
  `sms_hdfcbk_bill_due`);
- questions: `query_<intent>`;
- skills: `skill_<category>`.

**Handler string:** `ability:<name>@v<version>`.

**Sandbox protocol** (`compiler/sandbox.py: run(code, inputs, timeout=15) -> [{"ok": True, "value": …} |
{"ok": False, "error": str}]`):
- The code is written to `<tmp>/ability.py`, with a runner script. The runner:
  - replaces `socket.socket`, `create_connection`, `getaddrinfo` and `socketpair` with a function raising
    `PermissionError`;
  - reads a JSON list of inputs from stdin, imports `ability`, and calls `extract` on each (an exception becomes
    `{"ok": False, "error": "<Type>: <msg>"[:300]}`);
  - swallows stdout during the calls and prints one JSON list.
- It runs as `python -I runner.py <tmp>` with `cwd=tmp` and `env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE":
  "1", "LANG": "C.UTF-8"}`.
- `preexec_fn` sets `RLIMIT_CPU` to 10 s and `RLIMIT_FSIZE` to 1 MiB.
- On timeout every input gets `timeout after Ns`; a non-zero exit gives every input `sandbox exited <rc>: <stderr
  tail>`.

**`compare(expected, got) -> list[bad_keys]`** (generator.py): for each key in `expected`:
- `provider`/`service`: `provider_match`;
- `topic`: any non-empty string;
- numbers: within 0.01, and bools excluded;
- strings: equal after strip + lower;
- anything else: equality.

A non-dict `got` → `["<not a dict>"]`.

**Export** (on `tested`): `<BRAIN_ABILITIES_DIR>/<name>/v<n>/` gets three files:
- `ability.py`;
- `cases.json` (`[{input, expected, held_out}]`, `ensure_ascii=False`, indent 1);
- `test_ability.py`: a standalone pytest file with its own `provider_match` and the source of `compare` (via
  `inspect.getsource`), parametrised over the cases with ids `<i>` / `<i>-heldout`.

## 8. Chat questions (`brain/query.py`)

```python
Intent = Literal["due_items", "appointments", "subscriptions", "documents", "medicines", "price_changes", "digest", "unknown"]
Period = Literal["next_7_days", "next_14_days", "next_30_days", "this_week", "this_month", "next_month",
                 "last_30_days", "upcoming", "all", "range"]
class QuerySpec(BaseModel):
    intent: Intent
    period: Period = "upcoming"
    provider: str | None = None
    start: str | None = None   # period "range": phrases as written ("1 june", "aug") or ISO
    end: str | None = None
```

- **`resolve(phrase, today, end=False)`:** `dateutil.parser.parse(phrase, default=datetime(today.year, 1, 1),
  dayfirst=True)`. A phrase with no day number (ignoring 4-digit years, and not an ISO date) means a bare month:
  the 1st of the month, or the month's last day when `end=True`.
- **`normalize(spec)`:** for `range`, start/end become ISO; for other periods, start/end are cleared. Specs are
  always stored and compared normalised (`_spec_dict`).
- **`window(period, today, spec)`:**

  | Period | Window |
  |---|---|
  | `range` | (start or 1970-01-01, end or 2100-01-01) |
  | `all` | (None, None) |
  | `last_30_days` | today−30 .. today |
  | `this_week` | today .. Sunday |
  | `this_month` | 1st .. month end |
  | `next_month` | next month, 1st .. end |
  | `next_7/14/30_days`, `upcoming` | today .. today+7/14/30, and +60 for `upcoming` |

- **`answer_for(s, spec)`:** fixed code, no LLM. The answer templates:
  - **due_items:** types bill/premium/renewal/subscription, not paid/declined, in the window, provider-filtered.
    `"N payment(s) due <when> (₹T in total):\n• Sun 25 Oct · HDFC Bank bill ₹13,903.23"`, marked
    ` ⚠️ check` if flagged. `"Nothing due <when>."` when empty.
  - **appointments:** type meeting. `"You have N appointment(s) <when>:\n• Fri 08 May 10:30 — Apollo Clinic (Sunita
    Sharma)"`, with ` · proposed, not confirmed` for proposed ones. `"No appointments <when>."` when empty.
  - **subscriptions:** `"You pay for N subscription(s) (₹T/month):\n• Netflix: ₹649/month"`.
  - **documents:** `"• PUC valid until 10 Nov 2026"`.
  - **medicines:** `"• thyroid tablet (Mom): 1 tablet at 08:00, 29 left"`.
  - **price_changes:** from audit rows `subscription_price_increase`.
  - **digest:** see below.
  - **`<when>` text:** `next_7_days` → "in the next 7 days", `next_14_days` → "in the next 2 weeks",
    `next_30_days` → "in the next 30 days", `this_week`, `this_month`, `next_month`, `last_30_days` → "in the last
    30 days", `upcoming` → "coming up", `all` → "on record". For `range`: `between 1 Aug 2026 and 15 Sep 2026` /
    `since …` / `until …`.
- **`digest(s, start, end, when)`:**
  - obligations with a due date in the window, grouped as:
    - `💳 Due (N, ₹T in total)`: bill/premium/renewal/subscription, marked ` ✓ paid`, ` ⚠️ check`;
    - `📅 Appointments (N)`: meetings, not declined, marked ` · not confirmed`;
    - `📌 Requests (N)`: every other type, not declined, ` — <note>` unless the note just repeats the type;
  - then `📨 Updates received (N)`: one line per source received in the window whose extract trace isn't
    `ignore`, `• 3 Aug · <facts(output_json)>`, at most 15 then `…and N more`;
  - header `Everything <when>:`; empty → `Nothing due and nothing received <when>.`
- **`facts(o)`** (shared with the simulation feed): `kind · provider · topic (unless it repeats the kind) · ₹old →
  ₹new | ₹amount · due 5 Jun`.
- **`answer(question, llm, fallback) -> {answer, handler, intent, spec, event}`:** see 04_COMPILER §6.

## 9. Rules (`brain/rules/*.yaml`, engine in `rules/__init__.py`)

```yaml
rule: <name>
description: <text>
when:
  type: <extraction type or event, e.g. subscription_price_change | medication_stock>
  condition: "<name> <op> <name|number>"     # op in > >= < <= == !=; optional
then:
  - <action>: {<spec>}                       # action in update_subscription | reminder | send_message
permissions: [state.write, reminder.create, chat.send_self]
```

- **Permissions:** `PERMISSION = {"update_subscription": "state.write", "reminder": "reminder.create",
  "send_message": "chat.send_self"}`. An action whose permission isn't listed is skipped with audit
  `action_denied`.
- **Context** (from the extraction, `exclude_none`) also has:
  - `service` = provider or service;
  - `effective_date` = due_date;
  - `stored_price` = the matching subscription's price, else `old_price`.
- `fmt()` renders integral floats without `.0` and dates as `%d %b %Y`.
- **Actions:**
  - `update_subscription` upserts price + effective_date;
  - `reminder` (`date_field`, `days_before`, `at`, `text`) returns a callable that creates the job with key
    `rule:<service>:<effective_date>:<days_before>`;
  - `send_message` (`template`) returns a callable for `notify.send_self`.
  - Callables run after commit. Each fired rule writes an audit row named after the rule.

**The three rules, verbatim:**
- `subscription_price_increase`: `new_price > stored_price` →
  - update_subscription;
  - a reminder 2 days before `effective_date` at 09:00: "{service} price rises to ₹{new_price} on
    {effective_date}. Keep it or cancel before then.";
  - send_message: "{service} is raising your price from ₹{stored_price} to ₹{new_price} on {effective_date}.
    Reply KEEP or CANCEL-HELP."
- `subscription_price_update`: `new_price <= stored_price` → update_subscription only.
- `medicine_refill`: when type `medication_stock`, condition `stock <= 5` → send_message "Only {stock} left of
  {whose} {name}. Time to order a refill."

## 10. Scheduler (`brain/scheduler.py`)

- **Setup:** APScheduler 3 `BackgroundScheduler` with `SQLAlchemyJobStore(engine=db.engine)`, timezone IST,
  `misfire_grace_time=3600`, `coalesce=True`. It is started paused unless asked (only the real bot runs it).
- **Functions:**
  - `now()` returns naive IST. The simulation monkey-patches `scheduler.now`, so **always call `scheduler.now()`**,
    never `datetime.now()`, for anything time-relative.
  - `create_reminder(text, run_at, key=None, **ref)` adds a date job calling `"brain.scheduler:fire_reminder"`
    with kwargs `{text, obligation_id?, medication_id?}`, `replace_existing=True`.
  - `create_repeating(cron, key, func_ref=FIRE, name, **kwargs)` uses a `CronTrigger.from_crontab(cron, tz=IST)`.
  - `remind_before(text, due, days, key, at="09:00", **ref)` returns None if that moment has passed.
  - `upcoming()` lists `[(next_run_time, text, job_id)]`.
- **`fire_reminder(text, obligation_id, medication_id, urgent=False)`:**
  - inside quiet hours (`BRAIN_QUIET_HOURS` "22-07", wrapping midnight) and not urgent → reschedule to the end of
    quiet hours;
  - otherwise merge every other FIRE date job due within 15 minutes (remove them), audit `reminded` per item, and
    send one message: the text alone, or `"Reminders:\n• a\n• b"`.
- **`fire_dose(medication_id)`:** "Time for {your|Mom's} {name} ({dose}). Reply 1 when taken."
- **Relative reminders for obligations** (`planner.plan_obligations`), `DAYS_BEFORE = {bill: 3, premium: 3,
  renewal: 7, meeting: 1}`:
  - text `"{provider} {type} ₹{amount} is due on {dd Mon}. Reply 'paid' when done, or 'snooze 1h'."`;
  - for meetings: `"{provider} appointment on {dd Mon}."`;
  - key `due:<obligation id>`.

## 11. Reply handlers (`brain/replies.py`), checked before anything else in chat

- **`^\s*(1|done|taken)\s*[.!]?\s*$`** → log a dose against the medication of the most recent `reminded` audit
  row that has `medication_id`:
  - stock −1 (min 0), add a `DoseLog`, audit `dose_logged`;
  - run rules for event `medication_stock` with `{name, stock, person, whose}`;
  - reply "Logged {whose} {name}. {stock} left."
- **`^\s*snooze\s+(\d+)\s*(m|min|mins|minutes?|h|hr|hrs|hours?)\s*$`** → re-create the last reminder at
  `scheduler.now() + delta` ("Snoozed until HH:MM.").
- **`^\s*paid(?:\s+(.+?))?\s*[.!]?\s*$`** → with a provider, the first open/flagged obligation matching it by
  due date; without one, the obligation of the last reminder. Status becomes `paid`, audit `mark_paid`.
- **No match** → None, and the text goes to the planner / the question pipeline.

## 12. Button actions (`brain/actions.py`): one grammar for Telegram and the web

| Action id | Effect | Extra keys in the result |
|---|---|---|
| `approve:<ability>` | `registry.approve` (latest `tested` → `shadow`, shadow_matches = 0) | |
| `reject:<ability>` | the latest `tested` → `retired` | |
| `meet:<source_id>:yes` | book the proposed slot | `title, link, meet, ics, followup` |
| `meet:<source_id>:other` | ask the user to type a time | `awaiting_time: source_id` |
| `meet:<source_id>:at:<YYYY-MM-DDTHH:MM>` | book at that time (the obligation moves; audit `meeting_moved{was, to}`) | as for yes |
| `meet:<source_id>:no` | decline | `followup` (a polite decline) |
| `mail:<source_id>:send` / `:skip` | send the drafted reply to the outbox, or record skipping | `sent: {to, subject, body}` |
| `skill:<category>:yes` / `:no` | accept (status active) or decline (retired) a proposed skill | `compile: category` on yes |

- Every result has `text`.
- `followup` is a `(text, actions)` pair the caller passes to `notify.ask_self`.
- `approval_prompt(result)` builds the ask after a successful compile: "🧪 New ability {name} v{n} passed its
  tests ({visible} shown + {held_out} held-out cases, held-out pass P%). It would {describe}. Approve it for
  shadow mode?", with buttons `✅ Approve` / `❌ Reject`.

## 13. Meetings (`brain/meetings.py`)

- **Details** are parsed from the obligation note (`HH:MM · person · topic`). `start_of(ob)` = due_date + time
  (default 09:00). `title_of(ob)` = `"{topic or 'Meeting'} with {person or provider}"`.
- **Prompt:**
  ```
  📅 Meeting request from {person} ({provider})
  About: {topic}
  They proposed: {Thu 29 Oct, 11:00 AM}

  Do you want to meet? Pick a time:
  ```
  with buttons `✅ <slot>` (`meet:id:yes`), `🕐 Another time` (`meet:id:other`), `❌ Decline` (`meet:id:no`).
- **`parse_when(text, base)`:**
  - returns None unless the text has a digit, a weekday or month prefix, `today`, `tomorrow` or `noon`;
  - `today`/`tomorrow` set the default date (from `scheduler.now()`), keeping the base time;
  - then `dateutil.parse(text, default=base, fuzzy=True, dayfirst=True)`; a weekday alone moves to the next such
    day on or after the default;
  - a result in the past → None.
- **`decide(id, accept, at=None)`:**
  - a meeting that is already open or declined → "Already accepted/declined: …";
  - accepting sets status `open`, with reminders "Tomorrow: …" 1 day before at 09:00 (`meet:<ob>:1d`) and "In 1
    hour: …" (`meet:<ob>:1h`, if still in the future);
  - `meet_link(ob_id)` is a placeholder in Meet format from sha256(`sorted-meet-<id>`): `xxx-xxxx-xxx` from
    `abcdefghijkmnopqrstuvwxyz`;
  - `google_link(title, start, 60, info)` → `https://calendar.google.com/calendar/render?action=TEMPLATE&text=…
    &dates=YYYYMMDDTHHMMSS/…&ctz=Asia/Kolkata&details=…`;
  - `ics(title, start, uid, 60, location=meet)`.
- **`draft(id)`:** None unless the source is an email with an address. Otherwise:
  - `{to: src.sender, subject: "Re: <subject>", body}`;
  - the body starts "Hi {first name},\n\nThanks for getting in touch about {topic}." followed by one of:
    - "{Friday 30 October at 5:00 PM} works for me.\nGoogle Meet: …" (accepted);
    - "{was} doesn't suit me, but I can do {when}.\nGoogle Meet: …" (moved);
    - "Unfortunately I can't make it, so let's skip this one for now." (declined);
  - it ends "\n\nBest regards" + ",\n{BRAIN_USER_NAME}" when that name is set.
- **`followup(id)`:** "✉️ Shall I reply?\n\nTo: …\nSubject: …\n\n<body>" with `📤 Send` / `Don't send`.
- **`send(id, yes)`:** idempotent per source; audit `email_sent{source, to, subject, body}` or `email_skipped`.
  **The outbox = audit rows `email_sent`.**

## 14. Skills (`brain/skills.py`)

See 04_COMPILER §7. `ACTIONS = {remind_before_due: "remind you the day before each one's date",
notify_on_arrival: "message you as soon as one arrives", track_only: "keep them on a list you can ask about"}`.

## 15. Interfaces

### CLI (`brain`, argparse subcommands)

| Command | Does |
|---|---|
| `init` | create the schema |
| `stats` | row counts per table |
| `ingest [paths…] [--until YYYY-MM]` | ingest the fixtures (default) or the given `.eml`/`.pdf` files |
| `imap [--since YYYY-MM-DD] [--limit 100]` | read-only IMAP (`IMAP_HOST`/`IMAP_USER`/`IMAP_PASSWORD`) |
| `drain` | retry queued sources |
| `ask "<question>"` | the question pipeline |
| `compile` | detect + compile pending abilities |
| `approve <name>` | tested → shadow |
| `abilities` | list with health stats |
| `score [--demo]` | privacy score + cost per message (the live DB, or `data/demo.db`) |
| `fetch <url>` | TinyFish Fetch into the pipeline |
| `portal <url> "<goal>" [--record]` | TinyFish Agent (replayed unless `TINYFISH_LIVE=1`) |
| `due` | due in the next 7 days, no LLM |
| `say "<text>"` | chat as if on Telegram (replies → planner → questions) |
| `serve-sms` | uvicorn on 127.0.0.1:8787 for `POST /ingest/sms` |

### Real-use Telegram bot (`make bot`, the live DB, scheduler running)

- **Owner:** `TELEGRAM_OWNER_ID`, or the first chat to send `/start` (stored in `data/telegram_owner`); every
  other chat is ignored.
- **Commands:**
  - `/start`, `/help`;
  - `/due` (7 days, no LLM; declined meetings hidden, proposed ones marked);
  - `/score [demo]` (a `<pre>` table);
  - `/abilities`, `/approve <name>`, `/audit` (the last 10 audit rows);
  - `/portal <url> <goal>`.
- **Other input:** PDF documents are ingested; photos get "OCR is on the roadmap"; text goes through replies →
  planner → questions.
- **Reminders:** a sink sends to the owner.

### Simulation Telegram front end and web API
See 06_SIMULATION_AND_UI.

### MCP server (`brain/mcp_server.py`, `MCPServer("sorted", instructions=...)`)

- **Tools:**
  - `get_upcoming(days=7, type=None)`, `search_obligations(query)`, `get_obligation(id)` (with its source);
  - `mark_paid(id)` (write), `create_reminder(text, when ISO)` (write; key `mcp:<hex>`);
  - `list_abilities()`, `run_ability(name, input)` (only `active` abilities, sandboxed; the input is redacted);
  - `get_privacy_score()`.
- **Resources:** `sorted://profile` (JSON), `sorted://digest` (text).
- **Prompts:** `weekly_review`, `what_do_i_owe_this_month`.
- **Write tools** call `_require_write()` (`BRAIN_MCP_SCOPE` must be `read-write`) and audit with actor `mcp`.
- **Transports:** stdio by default. `--http` serves `server.streamable_http_app()` wrapped in an ASGI bearer
  middleware (`Authorization: Bearer $BRAIN_MCP_TOKEN`, else 401 `{"error": "unauthorized"}`) on
  `BRAIN_MCP_HOST:BRAIN_MCP_PORT` (127.0.0.1:8765).

### SMS webhook (`brain/sources/sms_api.py`)

- `POST /ingest/sms` with `{sender, body, received_at?}`.
- Auth: `Authorization: Bearer <token>` checked with `secrets.compare_digest` against `BRAIN_INGEST_TOKENS =
  "name:token,name:token"`; failure → 401.
- Ingests `Message("sms", sender, "", body, received, "sms:webhook:<user>")` and returns the orchestrator result
  without `extraction`.

### TinyFish (`brain/sources/tinyfish.py`, header `X-API-Key: $TINYFISH_API_KEY`)

- **URLs:** Fetch `https://api.fetch.tinyfish.ai`, Search `https://api.search.tinyfish.ai`, Agent
  `https://agent.tinyfish.ai/v1/automation/run` (`{url, goal, browser_profile: "lite", output_schema}`, timeout
  180 s).
- **No key:** `NotConfigured` with a clear message.
- **Agent:** only live with `TINYFISH_LIVE=1`; otherwise it replays
  `tests/fixtures/tinyfish/agent_<sha256(url|goal)[:12]>.json` (`{url, goal, recorded_at, response}`), or raises
  `NotConfigured`.
- **`portal(url, goal, schema)`:** stores a `SourceRecord(kind="web")` and a `portal` trace. A result with
  `amount_due` + `due_date` (the `BILL_SCHEMA`) also becomes a bill obligation. `PRICE_SCHEMA` is
  `{provider, plan, price, currency}`.
- **`fetch_message(url)`:** a `web` Message through the normal pipeline.

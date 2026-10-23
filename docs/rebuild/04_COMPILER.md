# 04: The compiler, its lifecycle, compiled questions, new skills, the classifier

## 1. Detector (`brain/compiler/detector.py`)

- **`subject_words(subject)`:** lower-cased `[a-z]+` words of length ≥ 4, excluding:
  - stop words `{your, from, with, this, that, have, ready, here, about}`;
  - month names `{january, february, march, april, june, july, august, september, october, november, december,
    sept}`;
  - redaction masks (words made only of `x`).
- **`groups(s)`:**
  - takes every accepted `extract` trace with `handler == "llm"`, joined to its source;
  - the key is `(src.kind, sender_key(src.kind, src.sender), etype)`, where `etype` is `output_json["type"]`, or
    `output_json["category"]` when the type is `other`;
  - `ignore` is excluded: dropping ignorable mail is the classifier's job, not a parser's.
- **`make_trigger(key, items)`:** `{kind, sender_key, type: etype, subject_keywords}`. The keywords are the
  sorted first 6 of the intersection of every item's `subject_words`, for email only (empty for SMS).
- **`scan(s)`**, for each group:
  - **a new category** (etype not in `validate.TYPES`) is skipped unless `skills.is_active(s, etype)`, i.e. the
    user agreed to learn it;
  - **no ability with that name yet,** and ≥ `BRAIN_COMPILE_AFTER` (3) items → a new `Ability(kind="parser",
    version=1, status="candidate", trigger, permissions=["read:message_text"])`;
  - **latest is `candidate`** (failed before) and the group has more items than its `trigger_json["n_traces"]` →
    recompile it;
  - **latest is `degraded`** and some item's source id ≥ `repair_from_source` → a new version n+1 `candidate`,
    keeping `repair_from_source`.

  `flush()` happens before returning, so new candidates get ids.
- **`items_for(s, ability)`:** the group for that ability's trigger.

## 2. Compiler loop (`brain/compiler/generator.py: compile_ability`)

1. **Cases:** `items = items_for(s, ability)`; `cases = split_cases(ability, items)`, one per trace: `{input:
   src.text, expected: trace.output_json, source_id, held_out}`.
2. **Held-out split:**
   - `n_held = round(len * 0.3)` if there are ≥ 3 cases, else 0;
   - for a repair, every case with `source_id >= repair_from_source` must be visible (the new layout must be
     shown);
   - otherwise at least one case stays visible;
   - the held-out indices are chosen with `random.Random(f"{name}@{version}").sample(pool, n_held)`, so the split
     is deterministic.
3. **Store the tests:** replace this ability's `ability_tests` rows with the cases.
4. **Output fields:** the fields from `FIELD_ORDER` present in any visible expected output.
5. **Attempts** (at most 2), with cache key `compile:<name>:v<version>:n<len(items)>:attempt<k>`. Each attempt:
   - calls the strong route with `COMPILER_SYSTEM` and the user turn from 03_PROMPTS §5, plus the previous
     code and problems on attempt 2;
   - prefixes `HEADER`;
   - runs `static_check.check(code)`. If there are problems, the feedback is "Static check rejected the code:…"
     and the attempt counts;
   - otherwise sets `status = "generated"` and runs **all** cases in one sandbox call:
     - a visible case fails when the sandbox errors or `compare` returns bad keys; the feedback line is
       `example i: expected {...} got {...} (wrong: [...])`;
     - for held-out failures, only the count is fed back: "N of M held-out cases (not shown to you) also failed;
       generalise.";
   - **passes** when no visible case fails and the held-out pass rate is ≥ 0.98 → `status = "tested"`, then
     `export()`.
6. **Not tested after 2 attempts** → `status = "candidate"`, `last_error = feedback[:2000]`.
7. **The LLM is unavailable** (budget/key/API error) → stop with that feedback.
8. **Always:**
   - set `trigger_json["n_traces"] = len(items)`;
   - add `Trace(task_kind="compile", handler="llm", tokens, cost, input_ref=last item's source,
     accepted=tested, output_json={ability, version, status, visible, held_out, held_out_pass_rate})`;
   - audit `compiled`;
   - return `{ability, version, status, visible, held_out, held_out_pass_rate, tokens, error}`.

`compile_pending(s, llm, only_type=None)` runs `[compile_ability(ab) for ab in detector.scan(s) if only_type
is None or ab.trigger_json["type"] == only_type]`.

## 3. Static check (`brain/compiler/static_check.py`), verbatim lists

```python
ALLOWED_IMPORTS = {"re", "datetime", "decimal", "html", "json", "dateutil", "typing"}
BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr",
    "delattr", "input", "breakpoint", "help", "exit", "quit", "memoryview", "os", "sys", "subprocess",
    "socket", "requests", "shutil", "pathlib", "importlib", "builtins"}
BANNED_ATTRS = {"system", "popen", "unlink", "remove", "rmdir", "rmtree", "kill", "fork", "spawn"}
```

The check walks the AST and reports each problem with its line number:
- imports outside the allowlist (relative imports included);
- a banned name, or any name starting with `__`;
- a banned attribute, or any attribute starting with `__`;
- `global` / `nonlocal`;
- a module that doesn't define a top-level `def extract`;
- a syntax error.

## 4. Lifecycle at runtime (`brain/compiler/registry.py`)

```
candidate --compile ok--> tested --user approves--> shadow --N matching runs--> active
    ^  \--compile fails--> candidate (retried when more traces exist)   |
    |                                                                   | output fails validation / shadow mismatch
    +------------------ v(n+1) candidate <------------------------------ degraded
active older versions --(newer version activates)--> retired
```

- **`match(s, src)`:** among abilities with status active/shadow, ordered by version descending, the first
  whose trigger matches:
  - same kind;
  - same `sender_key`;
  - `subject_keywords ⊆ subject_words(src.subject)`.
- **`execute(ab, src)`:**
  - runs the sandbox with a 10 s timeout, `runs += 1`;
  - **failure** is any of: a sandbox error; an empty result ("trigger matched but extraction is empty");
    `Extraction.model_validate` failing ("output schema: …"); or `validate()` problems ("validation: …");
  - on failure, `failures += 1` and `last_error`, returning `(None, reason)`;
  - **the orchestrator then degrades it** and falls back to the LLM.
- **`shadow(s, ab, src, llm_ext)`:**
  - runs the ability; `expected` = the LLM extraction restricted to `CORE_FIELDS = (type, provider, amount,
    due_date)` plus any key the ability itself output;
  - a mismatch → `failures += 1`, degrade, and the event "shadow mismatch -> degraded";
  - a match → `shadow_matches += 1`. When it reaches `BRAIN_SHADOW_RUNS` (default 2; the demo and sim use 1),
    `activate()`. The event is "shadow match k/N" or "shadow match k/N -> active".
- **`activate`:** status `active`, older non-retired versions → `retired`, audit `activated`.
- **`degrade(s, ab, reason, src)`:** status `degraded`, `last_error`, `repair_from_source = src.id`, audit
  `degraded`.
- **`approve(s, name, actor)`:** the latest `tested` version → `shadow`, `shadow_matches = 0`, audit `approved`.

## 5. Local classifier (`brain/ml/`)

- **`EmailClassifier.fit(examples)`:**
  - **layer 1 (rules):** for each `(sender_key, label)` with ≥ 2 examples, the intersection of their
    `subject_words(subject or text)`;
  - **layer 2:** `make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True), LogisticRegression(C=10,
    max_iter=2000))` on the redacted text, when there are ≥ 2 labels.
- **`predict(kind, sender, subject, text) -> (label, confidence, layer)`:**
  - exactly one rule hit → `(label, 1.0, "rule")`;
  - else the TF-IDF argmax probability, layer `"tfidf"`;
  - no model → `(None, 0, "none")`.
- **The orchestrator acts only on a confident `ignore`:** confidence ≥ `BRAIN_CLASSIFIER_THRESHOLD` (0.7) → handler
  `ml:<layer>`, and the LLM is skipped. Anything else goes on to the LLM.
- **Persistence:** `MODEL_PATH = ROOT / BRAIN_MODEL_DIR (default data/models) / "classifier.joblib"`.
  `current()` loads and caches it; `set_current()` replaces it.
- **Training:**
  - `train(examples)` dedupes by text, fits, saves, sets current;
  - `trace_examples()` = accepted LLM extract traces;
  - `labelled_examples()` = the committed samples minus OTPs;
  - **retraining** happens at each Sim month end on `trace_examples()` only, so nothing is learned from future
    months.
- **`held_out_report(seed)`:** a stratified 70/30 split of the labelled examples; classes with fewer than 2
  examples are train-only. Returns accuracy, the share of predictions with confidence ≥ threshold, and their
  accuracy. `make eval` averages seeds (1, 2, 3, 7, 11).

## 6. Compiled questions (`brain/query.py`)

**`answer(question, llm, fallback)`:**
1. **Record the question:** `text = redact(question)`, stored as `SourceRecord(kind="chat", sender="user",
   subject="question", body_hash=uuid, received_at=scheduler.now(), status="done")`.
2. **Try the compiled recognisers:** `live` = query abilities with status active or shadow. Run each recogniser
   (sandbox, 10 s): a non-empty dict that validates as `QuerySpec` is a hit.
3. **Exactly one active hit** → `runs += 1`, handler `ability:query_<intent>@v<n>`, event "answered by compiled
   code, 0 LLM calls".
4. **Otherwise ask the LLM:** `llm.json("small", PLANNER_SYSTEM, text, QuerySpec)`. On an error, return "I can't
   answer right now (…)". Then, for each live ability of the same intent:
   - **in shadow:** a hit whose normalised spec equals the LLM's → `shadow_matches += 1`, activating at
     `BRAIN_SHADOW_RUNS` ("… matched the LLM -> active"); otherwise degrade ("disagreed with the LLM ->
     degraded");
   - **active but it missed** (no hit): `failures += 1`, `last_error = "missed: <q>"`. At
     `MISSES_BEFORE_REPAIR = 2` misses, degrade, and v(n+1) will learn the phrasing.
5. **Reply:** `fallback(question)` (LLM free chat) for intent `unknown`, else `answer_for(s, spec)`.
6. **Trace:** `Trace(task_kind="query", input_ref=src.id, handler, tokens, cost, output_json=normalised spec,
   accepted=intent != "unknown")`.

**Compiling recognisers:**
- **`groups(s)`:** `query` traces with `handler == "llm"`, keyed by intent.
- **`scan(s)`:** for each intent except `unknown`, with name `query_<intent>`:
  - no ability yet and ≥ 3 traces → a new candidate (`kind="query"`, trigger `{kind: "query", intent}`,
    permissions `["read:question_text"]`);
  - a candidate with more traces than `n_traces` → recompile;
  - degraded with new traces since `repair_from_source` → v(n+1).
- **`compile_ability`:**
  - **positives** come from `split_cases` over that intent's traces;
  - **negatives:** up to 6 distinct question texts from other intents, shuffled with `Random(name)`, expected
    None, alternating visible/held-out; they are stored with expected `{"no_match": True}`;
  - the prompt is 03_PROMPTS §7;
  - a positive passes if `compare(expected, normalised(value))` is empty; a negative passes only if the code
    raised or returned falsy;
  - **same pass rule as parsers;** the header fields are `["intent", "period", "provider", "start", "end"]`;
  - **not exported** to `abilities/`.
- **When it compiles:**
  - in the simulation, right after an answer whenever `scan` finds candidates (a background thread);
  - and at every Sim month end in both `make demo` and `make sim`.

## 7. New kinds of messages → skills (`brain/skills.py`)

1. **The extractor names new kinds.** It may answer `type="other"` with an invented snake_case `category`. The
   user turn lists `KNOWN CATEGORIES` so labels stay stable.
2. **`categories(s)`:** accepted `extract` traces (any handler) with `type == other` and a category, grouped by
   category.
3. **`scan(s)`:** a category with ≥ 3 items and no ability `skill_<category>` → `Ability(kind="skill",
   status="candidate", trigger={kind: "skill", category}, permissions=["read:extractions"])`.
4. **`plan(s, ab, llm)`:** one small-route call (03_PROMPTS §8). It stores `trigger_json.plan = {title, action,
   why}`, `n_traces`, and `senders` (the sorted providers). It adds a `plan_skill` trace and audit
   `proposed{skill, plan}`.
5. **`prompt(ab)`:**
   ```
   🆕 New kind of message: {title}
   I've seen {n} so far (from {≤3 senders}) and have no skill for them.

   I can learn one:
   • write and test code that reads them, so they stop going to the AI
   • {ACTIONS[action]}

   {why}

   Learn this skill?
   ```
   with buttons `✅ Learn it` (`skill:<cat>:yes`) and `Not now` (`skill:<cat>:no`).
6. **`decide(category, yes)`:** candidate → active / retired, audit `skill_accepted` / `skill_declined`. On yes
   it returns `compile: category`, and the caller then runs `compile_pending(s, llm, only_type=category)` in a
   background thread. Parsers are still per sender, so one needs 3 messages from one sender.
7. **`effects(s, ext, source_id)`** (called by the orchestrator for valid `other` extractions) for an active
   skill:
   - `remind_before_due` with a due date → `scheduler.remind_before("<Singular title> due tomorrow: <provider —
     topic>.", due, 1, key="skill:<source_id>")`;
   - `remind_before_due` without a date, or `notify_on_arrival` → `notify.send_self("📦 New <singular title
     lower>: <provider — topic> (by dd Mon).")`;
   - `track_only` → nothing; the obligation row is the list.
8. **Re-assessment:** the simulation calls `skills.scan` + `plan` after **every delivered message**
   (`Engine._reassess`). With auto-approve on it accepts immediately; otherwise it asks.

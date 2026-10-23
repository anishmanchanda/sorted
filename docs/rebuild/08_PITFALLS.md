# 08: Pitfalls: lessons learned the hard way

Read this before writing code. Each item cost real debugging time in the original build.

## Environment and processes
1. **Env is read at import time.** `config.DB_URL`, `db.engine` and `classifier.MODEL_PATH` are module
   globals. The demo and the simulation must set `BRAIN_DB_URL` etc. **before** the first `import brain…`
   (`demo.py` sets `os.environ` at the very top; `python -m brain.web` calls `sim_env.use()` first). Otherwise
   they silently write to the live `data/brain.db`.
2. **Two databases, never mixed.** `data/brain.db` (bot, MCP, CLI) and `data/demo.db` (demo, sim). `score
   --demo` / `/score demo` read the demo one.
3. **Relative env paths** (`BRAIN_SAMPLES_DIR=data/samples`) must resolve against the repo root, not the
   current directory, or `make eval` fails with a `ValueError` from a path outside the repo.
4. **One Telegram token = one poller.** `make sim` and `make bot` cannot run together.
5. **Tests use an in-memory SQLite** (`sqlite://`). Without `StaticPool` + `check_same_thread=False`, each
   connection gets its own empty database and threads (FastAPI's TestClient, the sim's compile threads) see no
   tables.

## Time
6. **Always call `scheduler.now()`, never `datetime.now()`,** for anything relative to "now". The simulation
   monkey-patches `scheduler.now` to its clock; `config.today()` honours `BRAIN_TODAY`, which the sim sets.
7. **Month-end work must run while the clock is still inside that month.** Otherwise its feed events land in
   the next month and the recaps are wrong.
8. **The final month needs an explicit pass.** `advance()` closes months only when the clock passes their end.
   Sim month 6 ends exactly at `end()`, so its compile/repair runs only through `final_tasks_done`. Without it the
   HDFC v2 repair never happens.
9. **Don't schedule into the past.** `remind_before` returns None when the moment has passed. The dataset is
   shifted so its timeline ends "today".

## Replay cache
10. **Key demo extraction calls by sample id** (`extract:<id>`), not by prompt text. Otherwise shifting the
    dataset (different dates in the text) misses the whole cache.
11. **Shift dates on replay** by `current offset − recorded offset`, but only for keyed calls.
12. **Only committed samples get cache keys.** Messages you add or generate in the sim reuse ids like
    `m3_user5`, which collide across resets, so a key would replay a different message's answer. Use
    `cache_key` only when `raw_path` is under `data/samples/`.
13. **The compile cache key must include the number of traces** (`…:n<len(items)>:attempt<k>`). Otherwise a
    failed compile replays forever even after more examples arrive.
14. **Changing any system prompt invalidates every recorded call that used it.** Delete `data/llm_cache/`, run
    `make demo` with keys to re-record (≈ 80 calls), commit the cache + `reports/` + `abilities/`, and update the
    README numbers from `reports/`. Text added to the *user* turn does not change keyed cache entries, which is
    how the compiler's topic hint was added without a re-record.

## Compiler
15. **Parsers are per sender.** Layouts differ between senders, so a category whose messages come from many
    senders gets a skill (its action works) but no parser until one sender has sent 3.
16. **Don't make the parser reproduce the LLM's free-text summary.** `topic` is compared as "any non-empty
    string". Exact comparison makes every compile of a meeting request or `other` message fail.
17. **Generated synthetic mail must be templated and plain ASCII.** Free-form prose with non-breaking hyphens
    and spaces (common in gpt-oss output) cannot be parsed by regex, so every compile fails. The generator prompt
    demands one fixed template per sender, and the engine translates Unicode punctuation to ASCII.
18. **A repair must show the new layout:** every case from `repair_from_source` on is visible, never held out.
19. **Shadow compares only the core fields plus what the ability outputs.** LLMs add optional extras
    (`service`, `person`…) that a parser may legitimately omit.
20. **A question's spec must be normalised before comparing** (date phrases → ISO), or "1 june" vs "2026-06-01"
    reads as a mismatch and degrades a correct recogniser.

## Pipeline and state
21. **Side effects after commit.** Reminders, alerts and asks are collected as callables (`after_commit`) and run
    after `s.commit()`. Running them inside the transaction gives "database is locked" and reminders for rows
    that later roll back.
22. **The classifier only short-circuits `ignore`.** Letting it decide bill types locally means wrong money facts
    with no validation path.
23. **OTP check before storage**, on subject + body. Only the fact that one was dropped is audited.
24. **Duplicates are not conflicts.** Same provider/type, same amount, same due date → link. Different amount or
    date within ±7 days → flag both, never overwrite.
25. **`subscription_receipt` updates the stored price** (what was charged is the current price). A price
    *change* is acted on only by the rules, which compare against the price stored *before* any rule ran.

## UI and Telegram
26. **CSS specificity:** `#modal{display:flex}` beats `.hidden{display:none}`. Add `#modal.hidden{display:none}`,
    or an invisible full-screen overlay blocks every click.
27. **Don't flood Telegram.** Send everything through one queue drained by one task with a delay. Using
    `run_coroutine_threadsafe` per message reorders them and trips rate limits.
28. **Editing a Telegram message with identical content raises `BadRequest`** (a double press). Catch it. Remove
    the inline keyboard when answering, so buttons can't be pressed twice.
29. **Telegram sometimes times out** (`NetworkError`). Retry a reply once.
30. **A reset started from Telegram restarts feed ids.** The dashboard must notice `feed_len < lastFeed` and clear
    itself.
31. **The autopilot must pause before manual steps** (`stop_autopilot(wait=True)`), or two threads move the clock.

## Process
32. **Commit identity:** use the repo's configured author; never pass `-c user.email=` inline.
33. **Never claim in the README what the code doesn't do,** and copy every number from `reports/`. Mark
    placeholders honestly: the Meet link, the outbox instead of real email, and synthetic data.

"""`make demo`: a synthetic simulation, written to reports/demo_run.md.

Six simulated months of fake household bills ("Sim month 1-6"), generated so the timeline ends on the run date:
nothing it schedules is in the past. Everything goes into data/demo.db, never the live DB the bot uses.

Sim month 1-3 the LLM handles everything; repeated senders become candidates, the compiler writes parsers and
tests them; the demo auto-approves (clearly printed); shadow runs compare against the LLM; then the same
senders run as local code. HDFC changes its email layout in Sim month 6: fallback to the LLM and a v2 compile.
A simulated clock fires reminders as their time comes.

LLM answers are recorded in data/llm_cache/ per message and replayed (dates moved with the timeline), so the
demo also runs with no API key. `make demo-live` ignores the cache and calls the providers.
"""

import calendar
import json
import os
import shutil
import sys
from datetime import date, datetime, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "data" / "demo"
CANON_END = date(2026, 9, 30)  # brain.samples.CANON_END (repeated: env must be set before brain imports)
# the committed synthetic dataset's simulated "today" (data/samples/dataset.json)
END = date.fromisoformat(json.loads((ROOT / "data" / "samples" / "dataset.json").read_text())["end"])
os.environ.update({
    "BRAIN_DB_URL": f"sqlite:///{ROOT / 'data' / 'demo.db'}",  # the simulation never touches the live DB
    "BRAIN_MODEL_DIR": str(DEMO / "models"),
    "BRAIN_ABILITIES_DIR": str(ROOT / "abilities"),  # committed: the code the demo compiled, for judges to read
    "BRAIN_SHADOW_RUNS": "1",  # demo only: one matching shadow run instead of the default 2
    "BRAIN_DATE_OFFSET": str((END - CANON_END).days),
})

from brain import config, db, notify, scheduler, score  # noqa: E402
from brain import eval as brain_eval  # noqa: E402
from brain.compiler import registry  # noqa: E402
from brain.compiler.generator import compile_pending  # noqa: E402
from brain.llm import LLM, LLMUnavailable  # noqa: E402
from brain.messages import sim_sample  # noqa: E402
from brain.ml import classifier  # noqa: E402
from brain.ml.train import trace_examples, train  # noqa: E402
from brain.orchestrator import Orchestrator  # noqa: E402
from brain.sources import tinyfish  # noqa: E402
from brain.sources.fixtures import load_fixtures  # noqa: E402

CACHE = config.ROOT / "data" / "llm_cache"
NETFLIX_PLANS = "https://help.netflix.com/en/node/24926"
NETFLIX_GOAL = ("Find the monthly price of the Netflix Standard plan (without ads). Return provider 'Netflix', the "
                "plan name, the monthly price as a number and the currency code.")
lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def money(x) -> str:
    return f"₹{x:,.2f}" if x is not None else ""


def describe(msg, out: dict) -> str:
    handler = out.get("handler", "")
    who = {"llm": "LLM", "": "-"}.get(handler, "LOCAL" if handler.startswith("ability:") else
                                       "LOCAL ML" if handler.startswith("ml:") else "RULE")
    if handler.startswith("ability:"):
        who += " " + handler.rsplit("@", 1)[1]
    ext = out.get("extraction")
    facts = ""
    if ext is not None and ext.type != "ignore":
        facts = f"{ext.provider} {money(ext.amount)} {'due ' + f'{ext.due_date:%d %b}' if ext.due_date else ''}"
    outcome = out["outcome"].replace("dropped_otp", "OTP dropped before storage")
    notes = [out.get("event")] + [f"rule fired: {r}" for r in out.get("rules", [])]
    if out.get("problems"):
        notes.append(f"flagged: {'; '.join(out['problems'])}")
    extra = "".join(f"\n      ↳ {x}" for x in notes if x)
    return (f"  {msg.received_at:%d %b} {msg.kind:5} {msg.sender_key[:24]:24} {who:9} "
            f"{(ext.type if ext else ''):26} {facts:38} [{outcome}]{extra}")


def month_end(n: int) -> datetime:
    """End of Sim month n on the run's timeline (canonical month n+3 of 2026, shifted)."""
    last = date(2026, n + 3, calendar.monthrange(2026, n + 3)[1]) + (END - CANON_END)
    return datetime.combine(last, time(18))


def fire_due(until: datetime) -> list[tuple[datetime, str]]:
    """The simulated clock reached `until`: reminders due by then fire (template text, no LLM)."""
    fired = []
    for job in scheduler.get().get_jobs():
        run_at = job.next_run_time.replace(tzinfo=None) if job.next_run_time else None
        if run_at and run_at <= until:
            fired.append((run_at, job.kwargs.get("text", job.name)))
            job.remove()
    return sorted(fired)


def main() -> None:
    live = "--live" in sys.argv
    llm = LLM(cache_dir=None if live else CACHE)
    say("# Sorted demo run (synthetic simulation)")
    say()
    say(f"`make demo{'-live' if live else ''}` replays 6 simulated months of synthetic bills in seconds to show how "
        f"the share of local code grows; no real user data or history. Dates are generated so the simulated "
        f"timeline ends on the run date ({END:%d %b %Y}); the simulation lives in `data/demo.db`, separate from "
        f"the live bot's database.")
    say()
    say(f"LLM routes: small={config.env('BRAIN_SMALL_PROVIDER')}/{config.env('BRAIN_SMALL_MODEL')}, "
        f"strong={config.env('BRAIN_STRONG_PROVIDER')}/{config.env('BRAIN_STRONG_MODEL')}. Compile after "
        f"{config.env('BRAIN_COMPILE_AFTER', '3')} accepted traces; shadow runs = 1 (demo setting; default 2). "
        f"Costs are estimates from BRAIN_PRICES.")
    say()
    say("```text")

    n_samples = len(load_fixtures())
    for stale in ("sim.json", "feed.jsonl"):  # the interactive simulation (make sim) starts fresh after this
        (DEMO / stale).unlink(missing_ok=True)
    db.Base.metadata.drop_all(db.engine)
    db.init_db()
    scheduler.get().remove_all_jobs()
    shutil.rmtree(config.ROOT / "abilities", ignore_errors=True)
    alerts: list[str] = []  # printed after the message line that caused them
    notify.SINKS[:] = [alerts.append]
    classifier.MODEL_PATH.unlink(missing_ok=True)
    classifier.set_current(None)  # the local classifier starts empty and learns from the LLM's labels
    real_now = scheduler.now

    orch = Orchestrator(llm=llm)
    msgs = load_fixtures()
    say(f"Generated {n_samples} synthetic messages (emails, SMS, PDFs) for Sim months 1-6.")
    for n in range(1, 7):
        say()
        say(f"=== Sim month {n} of 6 (synthetic) ===")
        for m in (m for m in msgs if sim_sample(m.raw_path)[1] == n):
            scheduler.now = lambda t=m.received_at: t  # simulated clock: "now" is when the message arrives
            say(describe(m, orch.ingest(m)))
            for text in alerts:
                say(f"      💬 chat alert to you: {text}")
            alerts.clear()
        until = min(month_end(n), datetime.combine(END, real_now().time()))  # the timeline ends at 'now'
        scheduler.now = lambda t=until: t
        for run_at, text in fire_due(until):
            say(f"  ⏰ {run_at:%d %b %H:%M} reminder fired by the scheduler (no LLM): {text}")
        with db.Session() as s:
            results = compile_pending(s, llm)
            s.commit()
        for r in results:
            say(f"  [compiler] {r['ability']} v{r['version']}: {r['status']} "
                f"({r['visible']} visible + {r['held_out']} held-out cases, "
                f"held-out pass {100 * r['held_out_pass_rate']:.0f}%, {r['tokens']} tokens)"
                + (f" — {r['error'][:160]}" if r["error"] else ""))
            if r["status"] == "tested":
                with db.Session() as s:
                    registry.approve(s, r["ability"], actor="demo")
                    s.commit()
                say(f"  [approval] auto-approved for demo: {r['ability']} v{r['version']} -> shadow "
                    f"(in real use: Telegram /approve or `brain approve`)")
        clf = train(trace_examples())  # only what the LLM labelled so far: no peeking at future months
        say(f"  [ml] retrained the local classifier on {clf.n_examples} LLM-labelled messages "
            f"({len(clf.rules)} sender rules)")
        with db.Session() as s:
            row = next(r for r in score.monthly(s) if r["month"] == f"Sim month {n}")
        say(f"  -- {row['tasks']} messages, {row['local']} handled by local code, {row['llm_calls']} LLM calls, "
            f"privacy score {100 * row['privacy']:.0f}%")
    scheduler.now = real_now

    say("```")
    say()
    say("## Abilities")
    say()
    say("| ability | version | status | runs | failures | last error |")
    say("|---|---|---|---|---|---|")
    with db.Session() as s:
        for ab in registry.listing(s):
            say(f"| {ab.name} | v{ab.version} | {ab.status} | {ab.runs} | {ab.failures} | "
                f"{ab.last_error[:70].replace('|', '/')} |")
    say()
    say("Generated code and its tests: `abilities/<name>/v<n>/` (run them with `uv run pytest abilities`).")
    say()
    say("## Reminders still scheduled after the simulation (all in the future; fire with no LLM)")
    say()
    for run_at, text, _ in scheduler.upcoming():
        say(f"- {run_at:%d %b %Y %H:%M} — {text}")
    say()
    say("## TinyFish (web)")
    say()
    try:
        out = tinyfish.portal(NETFLIX_PLANS, NETFLIX_GOAL, schema=tinyfish.PRICE_SCHEMA)
        say(f"Agent API run ({'replayed from tests/fixtures/tinyfish/' if out['replayed'] else 'live'}) on "
            f"{NETFLIX_PLANS}: `{out.get('result')}`, stored as a `portal` trace so the task can graduate like "
            f"any other. (TinyFish proxies have no India exit, so the public page shows US pricing.)")
    except tinyfish.NotConfigured as e:
        say(f"Skipped: {e}")
    say()
    say("## Privacy score and cost per simulated month")
    say()
    say(score.summary())
    say()
    say("## Extraction accuracy (`make eval`)")
    say()
    say(brain_eval.run().split("## Dataset")[0].replace("# Extraction eval\n\n", ""))
    os.environ["BRAIN_TODAY"] = END.isoformat()
    q = "What do I need to pay in the next two weeks?"
    try:
        llm.route("small")
        say(f"## Chat (answers from the simulated state only)\n\n> {q}\n\n{orch.ask(q)}")
    except LLMUnavailable:
        say("## Chat\n\nSkipped: the chat answer needs an LLM key (not replayable across dates).")
    say()
    say(f"LLM calls this run: {llm.stats['live']} live, {llm.stats['replayed']} replayed from `data/llm_cache/`.")
    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "demo_run.md").write_text("\n".join(lines) + "\n")
    print("\nSaved reports/demo_run.md and reports/eval.md (simulation DB: data/demo.db)")


if __name__ == "__main__":
    main()

"""`make demo`: six simulated months of a household inbox, end to end, written to reports/demo_run.md.

Month 1-3 the LLM handles everything; repeated senders become candidates, the compiler writes parsers and
tests them; the demo auto-approves (clearly printed); shadow runs compare against the LLM; then the same
senders run as local code. HDFC changes its email layout in month 6: fallback to the LLM and a v2 compile.

LLM responses are recorded to data/llm_cache/ and replayed on later runs, so the demo also runs with no API
key. `make demo-live` ignores the cache and calls the providers.
"""

import os
import shutil
import sys
from datetime import datetime
from itertools import groupby

from brain import config

os.environ["BRAIN_SHADOW_RUNS"] = "1"  # demo only: one matching shadow run instead of the default 2

from brain import db, notify, scheduler, score  # noqa: E402
from brain import eval as brain_eval  # noqa: E402
from brain.compiler import registry  # noqa: E402
from brain.compiler.generator import compile_pending  # noqa: E402
from brain.llm import LLM  # noqa: E402
from brain.orchestrator import Orchestrator  # noqa: E402
from brain.sources.fixtures import load_fixtures  # noqa: E402

CACHE = config.ROOT / "data" / "llm_cache"
lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def money(x) -> str:
    return f"₹{x:,.2f}" if x is not None else ""


def describe(msg, out: dict) -> str:
    handler = out.get("handler", "")
    who = {"llm": "LLM", "": "-"}.get(handler, "LOCAL" if handler.startswith("ability:") else "RULE")
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


def main() -> None:
    live = "--live" in sys.argv
    llm = LLM(cache_dir=None if live else CACHE)
    say("# Sorted demo run")
    say()
    say(f"Generated {datetime.now():%Y-%m-%d %H:%M} by `make demo{'-live' if live else ''}`. "
        f"LLM routes: small={config.env('BRAIN_SMALL_PROVIDER')}/{config.env('BRAIN_SMALL_MODEL')}, "
        f"strong={config.env('BRAIN_STRONG_PROVIDER')}/{config.env('BRAIN_STRONG_MODEL')}. "
        f"Compile after {config.env('BRAIN_COMPILE_AFTER', '3')} accepted traces; shadow runs = 1 (demo setting; "
        f"default 2). Costs are estimates from BRAIN_PRICES.")
    say()
    say("```text")

    db.Base.metadata.drop_all(db.engine)
    db.init_db()
    scheduler.get().remove_all_jobs()
    shutil.rmtree(config.ROOT / "abilities", ignore_errors=True)
    notify.SINKS[:] = [lambda text: say(f"      💬 chat alert to you: {text}")]

    orch = Orchestrator(llm=llm)
    msgs = load_fixtures()
    for n, (month, batch) in enumerate(groupby(msgs, key=lambda m: f"{m.received_at:%Y-%m}"), 1):
        say()
        say(f"=== Month {n} · {datetime.strptime(month, '%Y-%m'):%B %Y} ===")
        for m in batch:
            say(describe(m, orch.ingest(m)))
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
        with db.Session() as s:
            row = next(r for r in score.monthly(s) if r["month"] == month)
        say(f"  -- {row['tasks']} messages, {row['local']} handled by local code, {row['llm_calls']} LLM calls, "
            f"privacy score {100 * row['privacy']:.0f}%")

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
    say("## Reminders scheduled (fire with no LLM)")
    say()
    for run_at, text, _ in scheduler.upcoming():
        say(f"- {run_at:%d %b %Y %H:%M} — {text}")
    say()
    say("## Privacy score and cost per simulated month")
    say()
    say(score.summary())
    say()
    say("## Extraction accuracy (`make eval`)")
    say()
    say(brain_eval.run().split("## Dataset")[0].replace("# Extraction eval\n\n", ""))
    os.environ["BRAIN_TODAY"] = "2026-09-30"
    q = "What do I need to pay in the first half of October?"
    say(f"## Chat (answers from state only, today = 30 Sep 2026)\n\n> {q}\n\n{orch.ask(q)}")
    say()
    say(f"LLM calls this run: {llm.stats['live']} live, {llm.stats['replayed']} replayed from `data/llm_cache/`.")
    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "demo_run.md").write_text("\n".join(lines) + "\n")
    print("\nSaved reports/demo_run.md and reports/eval.md")


if __name__ == "__main__":
    main()

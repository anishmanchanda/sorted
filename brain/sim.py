"""Interactive simulation: six months of a synthetic household inbox replayed on a clock you control.

You play the person the data belongs to, through the web dashboard and/or Telegram. Advancing the clock delivers
each message when it "arrives" (the real pipeline: OTP filter, redaction, compiled abilities or LLM, state,
rules), fires reminders through the real scheduler path (template text, no LLM), and at each Sim month end runs
the compiler and retrains the local classifier. You approve abilities and answer meeting requests with buttons.
Everything lives in data/demo.db; the process must call brain.sim_env.use() before importing brain modules.
"""

import calendar
import json
import os
import re
import shutil
import threading
from datetime import date, datetime, time, timedelta
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
from typing import Literal

import openai
from apscheduler.triggers.date import DateTrigger
from pydantic import BaseModel
from sqlalchemy import func, select

from brain import actions, config, db, meetings, notify, replies, samples, scheduler, score, skills
from brain import query as query_mod
from brain.compiler import detector, registry
from brain.compiler.generator import compile_pending
from brain.llm import LLM, BudgetExceeded, LLMUnavailable
from brain.messages import IST, Message, sim_sample, to_ist_naive
from brain.ml import classifier
from brain.ml.train import trace_examples, train
from brain.orchestrator import Orchestrator
from brain.planner import PlannerAgent
from brain.sources.fixtures import load_fixtures

CANON_END = samples.CANON_END
STEPS = {"day": timedelta(days=1), "week": timedelta(days=7)}
PLAN_HINT = re.compile(r"\b(remind|track|tablet|medicine|pill|daily|every (day|morning|night|week|month))\b", re.I)


def how(handler: str, event: str = "") -> str:
    """Who answered, in words, for chat replies on Telegram and the dashboard."""
    tag = ("⚡ compiled code · 0 AI calls" if handler.startswith("ability:") else
           "📏 rule · no AI" if handler.startswith("rule") else "🧠 AI" if handler == "llm" else handler)
    event = re.sub(r"ability:(\w+)@v(\d+)", r"\1 v\2", event or "")
    event = (event.replace("matched the LLM -> active", "agreed with the AI, so code answers from now on")
             .replace("disagreed with the LLM -> degraded", "disagreed with the AI, so it will be recompiled")
             .replace("-> LLM (it will learn it)", "so the AI answered (code will learn it)"))
    return f"{tag} · {event}" if event and not event.startswith(("answered by compiled", "reply rule")) else tag


ASCII = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u00a0": " ",
                       "\u202f": " ", "\u2009": " ", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


class GenMessage(BaseModel):
    kind: Literal["email", "sms"] = "email"
    sender: str  # "Name <addr@example.in>" for email, a short sender id for SMS
    subject: str = ""
    body: str
    at: str  # ISO datetime on the simulated timeline


class GenBatch(BaseModel):
    label: str  # what this batch is, e.g. "shipment requests from Acme Logistics"
    messages: list[GenMessage]


GEN_SYSTEM = """You write SYNTHETIC test messages for the demo inbox of Sorted, a household/small-business admin
assistant. The inbox belongs to a fictional person, Rohan Sharma (Delhi), who also runs a small trading business.
Write the messages the user's request describes. Return JSON
{"label": "<what these are, a few words>", "messages": [{"kind": "email"|"sms", "sender": ..., "subject": ...,
"body": ..., "at": "YYYY-MM-DDTHH:MM"}]}.
- Fictional people and companies only; email senders as "Name <someone@company.example.in>".
- A request about one business or person ("a business sending…", "my landlord…"): every message comes from that
  ONE sender (same name and address), like a real recurring correspondent. Several senders only when the request
  asks for several. Email unless SMS is asked for.
- A recurring sender uses the SAME template every time, as business systems do: a fixed subject pattern and the
  same labelled lines in the same order (e.g. "Order ref: ...", "Items: ...", "Order value: Rs 1,20,000",
  "Required dispatch date: 12 Jul 2026"), with a short free-text note. Only the values change.
- Plain ASCII text only (no non-breaking hyphens or spaces, no smart quotes).
- Each message realistic and different: its own reference numbers, quantities, amounts (INR) and concrete dates
  (e.g. a requested dispatch or reply-by date a few days after it was sent). Plain-text bodies, 40-120 words.
- Dates: TIMELINE gives the simulated inbox's span and the current simulated time. If the request names a period
  (e.g. "between June and August"), place every "at" inside it, in the timeline's year; otherwise spread the
  messages across the whole timeline. Irregular spacing when the request says sporadically.
- 4-8 messages unless the request asks for a number (max 12). Never include real personal data."""

class Engine:
    def __init__(self, llm: LLM | None = None, data_dir: Path | None = None):
        self.dir = data_dir or config.DEMO_DIR
        self.lock = threading.RLock()
        self.llm = llm or LLM(cache_dir=config.ROOT / "data" / "llm_cache")
        self.orch = Orchestrator(self.llm)
        self.planner = PlannerAgent(self.llm)
        self.feed: list[dict] = []
        self.state: dict = {}
        notify.SINKS.append(lambda text: self.emit("notify", text))
        notify.ASK_SINKS.append(lambda text, acts: self.emit("ask", text, actions=acts))
        scheduler.now = self.now  # the whole process runs on simulated time
        db.init_db()
        if (self.dir / "sim.json").exists():
            self.state = json.loads((self.dir / "sim.json").read_text())
            feed = self.dir / "feed.jsonl"
            self.feed = [json.loads(line) for line in feed.read_text().splitlines()] if feed.exists() else []
            self._env()
        else:
            self.reset()

    # ------------------------------------------------------------------ clock and state
    def now(self) -> datetime:
        return datetime.fromisoformat(self.state["clock"]) if self.state.get("clock") else datetime.now()

    def _env(self) -> None:
        os.environ["BRAIN_DATE_OFFSET"] = str(self.state["offset"])
        os.environ["BRAIN_TODAY"] = self.now().date().isoformat()

    def _save(self) -> None:
        (self.dir / "sim.json").write_text(json.dumps(self.state, indent=1))

    def end(self) -> datetime:
        return datetime.combine(date.fromisoformat(self.state["end"]), time(23, 59))

    def month_end(self, n: int) -> datetime:
        last = date(2026, n + 3, calendar.monthrange(2026, n + 3)[1]) + timedelta(days=self.state["offset"])
        return datetime.combine(last, time(23, 59))

    def month_of(self, t: datetime) -> int:
        return next((n for n in range(1, 7) if t <= self.month_end(n)), 6)

    def emit(self, kind: str, title: str, detail: str = "", handler: str = "", actions=None, **extra) -> dict:
        ev = {"id": len(self.feed) + 1, "sim_time": self.now().isoformat(timespec="minutes"),
              "sim_month": self.month_of(self.now()) if self.state.get("clock") else 0, "kind": kind,
              "title": title, "detail": detail, "handler": handler, "actions": [list(a) for a in actions or []],
              **extra}
        self.feed.append(ev)
        with open(self.dir / "feed.jsonl", "a") as f:
            f.write(json.dumps(ev, default=str) + "\n")
        return ev

    def reset(self) -> None:
        with self.lock:
            self.dir.mkdir(parents=True, exist_ok=True)
            end = samples.dataset_end()  # the committed dataset's simulated "today"
            db.Base.metadata.drop_all(db.engine)
            db.init_db()
            scheduler.get().remove_all_jobs()
            shutil.rmtree(Path(config.env("BRAIN_ABILITIES_DIR", str(self.dir / "abilities"))), ignore_errors=True)
            classifier.MODEL_PATH.unlink(missing_ok=True)
            classifier.set_current(None)
            (self.dir / "feed.jsonl").unlink(missing_ok=True)
            self.feed = []
            auto = bool(self.state.get("auto_approve"))
            self.state = {"end": end.isoformat(), "offset": (end - CANON_END).days, "month": 1, "delivered": [],
                          "auto_approve": auto}
            self._extend_end()
            first = min(m.received_at for m in self.messages())
            self.state["clock"] = datetime.combine(first.date() - timedelta(days=1), time(8)).isoformat()
            self._env()
            self._save()
            self.emit("system", "Simulation reset",
                      f"{len(self.messages())} synthetic messages over 6 simulated months ending {end:%d %b %Y}. "
                      "You are Rohan Sharma; advance the clock to let mail arrive.")

    # ------------------------------------------------------------------ the dataset
    def messages(self) -> list[Message]:
        extra = self.dir / "extra"
        msgs = load_fixtures(config.SAMPLES_DIR)
        if (extra / "sms" / "sms.jsonl").exists():
            msgs += load_fixtures(extra)
        return sorted(msgs, key=lambda m: m.received_at)

    def _extend_end(self) -> None:
        """Messages you added after the dataset's last day push the end of the timeline out."""
        last = max(m.received_at for m in self.messages()).date()
        self.state["end"] = max(date.fromisoformat(self.state["end"]), last).isoformat()

    def labels(self) -> dict:
        out = {}
        for path in (config.LABELS_PATH, self.dir / "extra" / "labels.jsonl"):
            if path.exists():
                out.update({(r := json.loads(line))["id"]: r for line in path.read_text().splitlines()})
        return out

    def clear_added(self) -> int:
        with self.lock:
            extra = self.dir / "extra"
            n = sum(1 for m in self.messages() if "/extra/" in m.raw_path)
            shutil.rmtree(extra, ignore_errors=True)
            self.emit("system", f"Removed {n} added message(s)", "Reset to replay without them.")
            return n

    def add_message(self, kind: str, sender: str, subject: str, body: str, at: datetime | None = None,
                    label: str = "your message") -> str:
        """A synthetic message of your own, delivered when the clock reaches `at` (default: one minute from now)."""
        at = at or self.now() + timedelta(minutes=1)
        extra = self.dir / "extra"
        for sub in ("email", "sms", "pdf"):
            (extra / sub).mkdir(parents=True, exist_ok=True)
        sms_file = extra / "sms" / "sms.jsonl"
        sms_file.touch()
        n = len(list((extra / "email").glob("*.eml"))) + len(sms_file.read_text().splitlines()) + 1
        sid = f"{'sms_' if kind == 'sms' else ''}m{self.month_of(at)}_user{n}"
        aware = at.replace(tzinfo=IST)
        if kind == "sms":
            with open(sms_file, "a") as f:
                row = {"id": sid, "sender": sender, "received_at": aware.isoformat(), "body": body}
                f.write(json.dumps(row) + "\n")
        else:
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = sender, samples.TO, subject
            msg["Date"] = format_datetime(aware)
            msg.set_content(body)
            (extra / "email" / f"{sid}.eml").write_bytes(bytes(msg))
        with open(extra / "labels.jsonl", "a") as f:
            f.write(json.dumps({"id": sid, "type": label}) + "\n")
        self.emit("system", f"Added your message {sid}", f"{kind} from {sender}, arrives {at:%d %b %H:%M}")
        return sid

    def generate(self, request: str) -> dict:
        """Synthetic messages from a description ("a business sending shipment requests between June and
        August"). One LLM call writes them; past-dated ones arrive at once (backfill), the rest as the clock
        moves. As they arrive, Sorted re-assesses what it could learn (see _reassess)."""
        with self.lock:
            first = datetime.combine(min(m.received_at for m in self.messages()).date() - timedelta(days=1), time(8))
            timeline = (f"TIMELINE: {first:%Y-%m-%d} to {self.end():%Y-%m-%d}; "
                        f"current simulated time {self.now():%Y-%m-%dT%H:%M}")
            try:
                res = self.llm.json("small", GEN_SYSTEM, f"{timeline}\n\nREQUEST: {request}", GenBatch, "generate")
            except (BudgetExceeded, LLMUnavailable, openai.APIError) as e:
                return {"error": f"Couldn't generate ({e}). Generating needs an API key in .env."}
            batch, ids, now = res.data, [], self.now()
            self.emit("system", f"Generating synthetic data: {batch.label}", f"request: {request}", handler="llm")
            for m in batch.messages[:12]:
                m.subject, m.body = m.subject.translate(ASCII), m.body.translate(ASCII)
                try:
                    at = datetime.fromisoformat(m.at).replace(tzinfo=None)
                except ValueError:
                    at = now + timedelta(days=len(ids) + 1)
                ids.append(self.add_message(m.kind, m.sender, m.subject, m.body, max(at, first), label=batch.label))
            self._extend_end()
            self._save()
            past = [i for i in ids if (m := self.message(i)) and m["time"] <= now.isoformat(timespec="minutes")]
            if past:
                self.emit("system", f"Backfilling {len(past)} message(s) dated before the current simulated time",
                          "they arrive now, in date order")
                self.advance(now)
            return {"label": batch.label, "ids": ids, "backfilled": len(past), "later": len(ids) - len(past),
                    "tokens": res.tokens}

    # ------------------------------------------------------------------ advancing time
    def _next_job(self, until: datetime):
        jobs = [(j.next_run_time.astimezone(IST).replace(tzinfo=None), j) for j in scheduler.get().get_jobs()
                if j.next_run_time]
        due = sorted(((t, j) for t, j in jobs if t <= until), key=lambda x: x[0])
        return due[0] if due else (None, None)

    def _fire(self, job) -> None:
        if isinstance(job.trigger, DateTrigger):
            job.remove()
            if job.func_ref == scheduler.FIRE:
                scheduler.fire_reminder(**job.kwargs)
            else:
                job.func(**job.kwargs)
        else:  # repeating (e.g. a daily dose): run it, then move it to its next time
            job.func(**job.kwargs)
            prev = job.next_run_time
            job.modify(next_run_time=job.trigger.get_next_fire_time(prev, prev + timedelta(seconds=1)))

    def _deliver(self, m: Message) -> None:
        out = self.orch.ingest(m)
        h = out.get("handler", "")
        label = ("dropped before storage" if out["outcome"] == "dropped_otp" else
                 "compiled code" if h.startswith("ability:") else "local ML" if h.startswith("ml:") else
                 "rule" if h.startswith("rule:") else "LLM" if h == "llm" else h)
        ext = out.get("extraction")
        facts = ""
        if ext is not None and ext.type != "ignore":
            facts = " · ".join(filter(None, [ext.type.replace("_", " "), ext.provider,
                                             f"₹{ext.amount:,.2f}" if ext.amount else "",
                                             f"{ext.due_date:%d %b}" if ext.due_date else ""]))
        notes = [out.get("event")] + [f"rule fired: {r}" for r in out.get("rules", [])] + out.get("problems", [])
        if ext is not None and ext.type == "other":
            facts = query_mod.facts(ext.model_dump(mode="json", exclude_none=True))
        self.emit("message", f"{m.kind} from {m.sender_key}: {m.subject or m.body[:60]}",
                  " — ".join(filter(None, [facts, *notes])), handler=h or out["outcome"], label=label,
                  sample=(sim_sample(m.raw_path) or ("", 0))[0], outcome=out["outcome"], facts=facts)
        self._reassess()

    def _reassess(self) -> None:
        """After every message: has a new kind of message repeated enough to learn a skill for it?"""
        with db.Session() as s:
            new = skills.scan(s)
            for ab in new:
                skills.plan(s, ab, self.llm)
            s.commit()
            prompts = [(ab.trigger_json["category"], skills.prompt(ab)) for ab in new]
        for cat, (text, acts) in prompts:
            self.emit("system", f"Re-assessing: a new kind of message keeps arriving ({cat.replace('_', ' ')})",
                      "proposing a new skill", handler="skills")
            if self.state.get("auto_approve"):
                self.act(f"skill:{cat}:yes", by="auto-approve")
            else:
                notify.ask_self(text, acts)

    def _month_tasks(self, n: int) -> None:
        """End of Sim month n: compile repeated patterns, retrain the classifier, ask for approvals."""
        with db.Session() as s:
            results = compile_pending(s, self.llm) + query_mod.compile_pending(s, self.llm)
            s.commit()
        clf = train(trace_examples())
        for r in results:
            self._report_compile(r)
        self.emit("system", f"End of Sim month {n}",
                  f"local classifier retrained on {clf.n_examples} LLM-labelled messages")

    def _report_compile(self, r: dict) -> None:
        self.emit("compile", f"Compiler: {r['ability']} v{r['version']} -> {r['status']}",
                  f"{r['visible']} shown + {r['held_out']} held-out cases, held-out pass "
                  f"{100 * r['held_out_pass_rate']:.0f}%, {r['tokens']} tokens"
                  + (f" — {r['error'][:200]}" if r["error"] else ""), handler="compiler")
        if r["status"] == "tested":
            if self.state.get("auto_approve"):
                out = actions.handle(f"approve:{r['ability']}")
                self.emit("action", f"Auto-approved for the demo: {out['text']}", f"approve:{r['ability']}",
                          handler="auto-approve")
            else:
                notify.ask_self(*actions.approval_prompt(r))

    def set_auto_approve(self, on: bool) -> None:
        with self.lock:
            self.state["auto_approve"] = on
            self._save()

    def _pending(self, until: datetime) -> list[Message]:
        delivered = set(self.state["delivered"])
        return [m for m in self.messages() if sim_sample(m.raw_path)
                and sim_sample(m.raw_path)[0] not in delivered and m.received_at <= until]

    def advance(self, until: datetime) -> list[dict]:
        with self.lock:
            start = len(self.feed)
            until = min(until, self.end())
            pending = self._pending(until)
            while True:
                t_job, job = self._next_job(until)
                t_msg = pending[0].received_at if pending else None
                t = min(x for x in (t_job, t_msg, until + timedelta(seconds=1)) if x is not None)
                if t > until:
                    break
                while self.state["month"] < 6 and t > self.month_end(self.state["month"]):
                    self._month_tasks(self.state["month"])
                    self.state["month"] += 1
                self.state["clock"] = max(self.now(), t).isoformat()
                self._env()
                if job is not None and (t_msg is None or t_job <= t_msg):
                    self._fire(job)
                else:
                    m = pending.pop(0)
                    self._deliver(m)
                    self.state["delivered"].append(sim_sample(m.raw_path)[0])
                self._save()
            while self.state["month"] < 6 and until > self.month_end(self.state["month"]):
                self._month_tasks(self.state["month"])
                self.state["month"] += 1
            self.state["clock"] = max(self.now(), until).isoformat()
            self._env()
            if until >= self.end() and not self.state.get("final_tasks_done"):  # the last month's compile/repair
                self.state["final_tasks_done"] = True
                self._month_tasks(6)
            self._save()
            return self.feed[start:]

    def step(self, to: str) -> list[dict]:
        if to == "next":
            t_job, _ = self._next_job(self.end())
            times = [m.received_at for m in self._pending(self.end())] + ([t_job] if t_job else [])
            return self.advance(min(times, default=self.end()))
        if to == "month":
            n = self.month_of(self.now())
            target = self.month_end(n) if self.now() < self.month_end(n) else self.month_end(min(n + 1, 6))
            return self.advance(target)
        if to == "end":
            return self.advance(self.end())
        return self.advance(self.now() + STEPS[to])

    # ------------------------------------------------------------------ you, talking to it
    def ask(self, text: str) -> dict:
        with self.lock:
            self.emit("you", text)
            if (sid := self.state.get("awaiting_time")) and meetings.WHEN_HINT.search(text):
                with db.Session() as s:
                    ob = meetings.obligation_for(s, sid)
                    base = meetings.start_of(ob) if ob else self.now()
                at = meetings.parse_when(text, base)
                if at is None:
                    out = {"answer": "I couldn't read a future time from that. "
                                     "Try \"Friday 5pm\" or \"14 Jun 11:30\".",
                           "handler": "rule:reply", "event": "time parser, no LLM"}
                    out["how"] = how(out["handler"], out["event"])
                    self.emit("chat", out["answer"], out["how"], handler=out["handler"])
                    return out
                res = self.act(f"meet:{sid}:at:{at:%Y-%m-%dT%H:%M}")
                return {"answer": res["text"], "handler": "rule:reply", "how": "📏 time parser · no AI",
                        **{k: res[k] for k in ("link", "meet") if k in res}}
            self.state.pop("awaiting_time", None)
            reply = replies.handle(text)
            if reply is not None:
                out = {"answer": reply, "handler": "rule:reply", "event": "reply rule, no LLM"}
            elif PLAN_HINT.search(text) and (planned := self.planner.plan(text)):
                out = {"answer": planned, "handler": "llm", "event": "planner (one LLM call); the job runs without AI"}
            else:
                out = self.orch.ask_detail(text)
            out["how"] = how(out.get("handler", ""), out.get("event", ""))
            self.emit("chat", out["answer"], out["how"], handler=out.get("handler", ""))
            with db.Session() as s:  # repeated question types compile right away, so you can watch it happen
                todo = bool(query_mod.scan(s))
                s.rollback()
            if todo:
                threading.Thread(target=self._compile_queries, daemon=True).start()
            return out

    def _compile_queries(self) -> None:
        with self.lock:
            self.emit("system", "You keep asking this kind of question: compiling it into code…")
            with db.Session() as s:
                results = query_mod.compile_pending(s, self.llm)
                s.commit()
            for r in results:
                self._report_compile(r)

    def act(self, action: str, by: str = "you") -> dict:
        with self.lock:
            out = actions.handle(action)
            self.emit("action", out["text"], action, handler=by, link=out.get("link"), meet=out.get("meet"))
            if out.get("awaiting_time"):
                self.state["awaiting_time"] = out["awaiting_time"]
                self._save()
            elif action.startswith("meet:"):
                self.state.pop("awaiting_time", None)
                self._save()
            if out.get("sent"):
                m = out["sent"]
                self.emit("outbox", f"Email to {m['to']}: {m['subject']}", m["body"], handler="you")
            if out.get("followup"):
                notify.ask_self(*out["followup"])
            if out.get("compile"):
                threading.Thread(target=self._compile_category, args=(out["compile"],), daemon=True).start()
            return out

    def _compile_category(self, category: str) -> None:
        with self.lock:
            self.emit("system", f"Compiling code for {category.replace('_', ' ')} messages…", handler="compiler")
            with db.Session() as s:
                results = compile_pending(s, self.llm, only_type=category)
                s.commit()
            for r in results:
                self._report_compile(r)
            if not results:
                self.emit("system", "Skill active; no code to compile yet",
                          "its action already runs for every message of this kind. Code to read them is compiled "
                          f"per sender, once one sender has sent {config.env('BRAIN_COMPILE_AFTER', '3')}.")

    # ------------------------------------------------------------------ what the dashboard shows
    def status(self) -> dict:
        answered = {e["detail"] for e in self.feed if e["kind"] == "action" and not e["detail"].endswith(":other")}
        answered |= {f"meet:{e['detail'].split(':')[1]}:yes" for e in self.feed
                     if e["kind"] == "action" and e["detail"].startswith("meet:") and ":at:" in e["detail"]}
        pending = [e for e in self.feed if e["kind"] == "ask" and not answered & {a for _, a in e["actions"]}]
        return {"clock": self.state["clock"], "month": self.month_of(self.now()), "end": self.state["end"],
                "delivered": len(self.state["delivered"]), "total": len(self.messages()),
                "auto_approve": bool(self.state.get("auto_approve")),
                "awaiting_time": self.state.get("awaiting_time"), "pending_actions": pending}

    def outbox(self) -> list[dict]:
        with db.Session() as s:
            return meetings.outbox(s)

    def stats(self) -> dict:
        with db.Session() as s:
            months = score.monthly(s)
            q = s.execute(select(db.Trace.handler, func.count()).where(db.Trace.task_kind == "query")
                          .group_by(db.Trace.handler)).all()
        tasks = sum(m["tasks"] for m in months)
        local = sum(m["local"] for m in months)
        return {"months": months, "messages": tasks, "local": local, "privacy": local / tasks if tasks else 0,
                "llm_calls": sum(m["llm_calls"] for m in months), "tokens": sum(m["tokens"] for m in months),
                "cost": sum(m["cost"] for m in months),
                "questions": {"llm": sum(n for h, n in q if h == "llm"),
                              "local": sum(n for h, n in q if h != "llm")}}

    def abilities(self) -> list[dict]:
        """Every ability with its path from LLM work to compiled code."""
        out = []
        with db.Session() as s:
            compiles = s.scalars(select(db.Trace).where(db.Trace.task_kind == "compile")
                                 .order_by(db.Trace.id.desc())).all()
            audit = s.scalars(select(db.AuditLog).order_by(db.AuditLog.id)).all()
            qgroups = query_mod.groups(s)
            cats = skills.categories(s)
            for ab in registry.listing(s):
                items = (qgroups.get(ab.trigger_json.get("intent"), []) if ab.kind == "query" else
                         cats.get(ab.trigger_json.get("category"), []) if ab.kind == "skill" else
                         detector.items_for(s, ab))
                mine = [t for t in compiles if t.output_json.get("ability") == ab.name
                        and t.output_json.get("version") == ab.version]
                local_runs = s.scalar(select(func.count()).select_from(db.Trace).where(
                    db.Trace.handler == registry.handler(ab)))
                tests = s.scalars(select(db.AbilityTest).where(db.AbilityTest.ability_id == ab.id)).all()
                out.append({
                    "name": ab.name, "kind": ab.kind, "version": ab.version, "status": ab.status,
                    "what": actions.describe(ab), "trigger": ab.trigger_json, "llm_solves": len(items),
                    "local_runs": local_runs, "runs": ab.runs, "failures": ab.failures,
                    "shadow_matches": ab.shadow_matches, "last_error": ab.last_error,
                    "compile": {**(mine[0].output_json if mine else {}), "tokens": sum(t.tokens for t in mine)},
                    "history": [a.action for a in audit if a.detail.get("ability") == ab.name
                                and a.detail.get("version") == ab.version],
                    "code": ab.code,
                    "tests": [{"input": t.input[:400], "expected": t.expected_output, "held_out": t.held_out}
                              for t in tests]})
        return out

    def dataset(self) -> list[dict]:
        labels = self.labels()
        delivered = set(self.state["delivered"])
        out = []
        for m in self.messages():
            sid, month = sim_sample(m.raw_path)
            out.append({"id": sid, "sim_month": month, "time": m.received_at.isoformat(timespec="minutes"),
                        "kind": m.kind, "sender": m.sender, "subject": m.subject or m.body[:80],
                        "label": labels.get(sid, {}).get("type", "your message"), "added": "/extra/" in m.raw_path,
                        "status": "delivered" if sid in delivered else "pending"})
        return out

    def message(self, sid: str) -> dict:
        m = next(m for m in self.messages() if sim_sample(m.raw_path)[0] == sid)
        ev = next((e for e in reversed(self.feed) if e.get("sample") == sid), None)
        return {"id": sid, "kind": m.kind, "sender": m.sender, "subject": m.subject,
                "time": to_ist_naive(m.received_at).isoformat(timespec="minutes"), "body": m.body,
                "redacted": m.redacted_text(), "result": ev}

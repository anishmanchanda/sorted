"""Durable reminders on APScheduler with the SQLAlchemy job store (same SQLite DB): jobs survive restarts.
A job's payload is a fixed function + fixed inputs (a template message), never a prompt.

Reminder kinds: one-time (`create_reminder`), repeating cron (`create_repeating`), relative to a date
(`remind_before`, e.g. 3 days before a due date). Quiet hours defer non-urgent reminders; reminders due within
MERGE_WINDOW of each other are merged into one message. Processes that only schedule (CLI, demo, MCP) start the
scheduler paused; the Telegram bot starts it running.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from brain import config, db, notify

IST = ZoneInfo("Asia/Kolkata")
FIRE = "brain.scheduler:fire_reminder"
MERGE_WINDOW = timedelta(minutes=15)
_scheduler: BackgroundScheduler | None = None


def get(paused: bool = True) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(engine=db.engine)}, timezone=IST,
            job_defaults={"misfire_grace_time": 3600, "coalesce": True})
        _scheduler.start(paused=paused)
    elif not paused:
        _scheduler.resume()
    return _scheduler


def now() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)


def quiet_window(spec: str | None = None) -> tuple[time, time]:
    start, end = (spec or config.env("BRAIN_QUIET_HOURS", "22-07")).split("-")
    return time(int(start)), time(int(end))


def in_quiet_hours(t: time, spec: str | None = None) -> bool:
    start, end = quiet_window(spec)
    return (t >= start or t < end) if start > end else start <= t < end


def after_quiet(at: datetime, spec: str | None = None) -> datetime:
    end = quiet_window(spec)[1]
    candidate = datetime.combine(at.date(), end)
    return candidate if candidate > at else candidate + timedelta(days=1)


def fire_reminder(text: str, obligation_id: int | None = None, medication_id: int | None = None,
                  urgent: bool = False) -> None:
    """Runs when a reminder is due. No LLM: a template message, merged with any reminder due soon."""
    t = now()
    ref = {"text": text, "obligation_id": obligation_id, "medication_id": medication_id}
    if not urgent and in_quiet_hours(t.time()):
        get().add_job(FIRE, "date", run_date=after_quiet(t), kwargs=ref, name=text[:100])
        return
    batch = [ref]
    for job in get().get_jobs():
        if (job.func_ref == FIRE and isinstance(job.trigger, DateTrigger) and job.next_run_time
                and job.next_run_time.astimezone(IST).replace(tzinfo=None) <= t + MERGE_WINDOW):
            batch.append({"text": job.kwargs["text"], "obligation_id": job.kwargs.get("obligation_id"),
                          "medication_id": job.kwargs.get("medication_id")})
            job.remove()
    with db.Session() as s:
        for r in batch:
            db.audit(s, "scheduler", "reminded", **r)
        s.commit()
    texts = [r["text"] for r in batch]
    notify.send_self(texts[0] if len(texts) == 1 else "Reminders:\n" + "\n".join(f"• {x}" for x in texts))


def fire_dose(medication_id: int) -> None:
    with db.Session() as s:
        med = s.get(db.Medication, medication_id)
    if med is not None:
        whose = "your" if med.person in ("me", "") else f"{med.person}'s"
        fire_reminder(f"Time for {whose} {med.name} ({med.dose}). Reply 1 when taken.", medication_id=med.id)


def create_reminder(text: str, run_at: datetime, key: str | None = None, **ref) -> str:
    job = get().add_job(FIRE, "date", run_date=run_at, kwargs={"text": text, **ref}, id=key, name=text[:100],
                        replace_existing=True)
    return job.id


def create_repeating(cron: str, key: str, func_ref: str = FIRE, name: str = "", **kwargs) -> str:
    job = get().add_job(func_ref, CronTrigger.from_crontab(cron, timezone=IST), kwargs=kwargs, id=key,
                        name=(name or kwargs.get("text", key))[:100], replace_existing=True)
    return job.id


def remind_before(text: str, due: date, days: int, key: str, at: str = "09:00", **ref) -> str | None:
    """Relative reminder: `days` before `due`. Skipped if that moment has already passed."""
    run_at = datetime.combine(due - timedelta(days=days), time.fromisoformat(at))
    return create_reminder(text, run_at, key=key, **ref) if run_at > now() else None


def upcoming() -> list[tuple[datetime, str, str]]:
    return sorted((j.next_run_time, j.kwargs.get("text", j.name), j.id) for j in get().get_jobs()
                  if j.next_run_time)

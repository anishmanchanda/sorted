"""Durable reminders on APScheduler with the SQLAlchemy job store (same SQLite DB): jobs survive restarts.
A job's payload is a fixed function + fixed inputs (a template message), never a prompt.

Processes that only schedule (CLI, demo, MCP) start the scheduler paused; the bot starts it running.
"""

from datetime import datetime

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from brain import db, notify

_scheduler: BackgroundScheduler | None = None


def get(paused: bool = True) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(engine=db.engine)}, timezone="Asia/Kolkata",
            job_defaults={"misfire_grace_time": 3600, "coalesce": True})
        _scheduler.start(paused=paused)
    elif not paused:
        _scheduler.resume()
    return _scheduler


def fire_reminder(text: str) -> None:
    notify.send_self(text)


def create_reminder(text: str, run_at: datetime, key: str | None = None) -> str:
    job = get().add_job("brain.scheduler:fire_reminder", "date", run_date=run_at, kwargs={"text": text}, id=key,
                        name=text[:100], replace_existing=True)
    return job.id


def upcoming() -> list[tuple[datetime, str, str]]:
    return sorted((j.next_run_time, j.kwargs.get("text", j.name), j.id) for j in get().get_jobs()
                  if j.next_run_time)

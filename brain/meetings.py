"""Meeting requests: someone asks for the user's time; Sorted asks the user whether and when to meet.

The user picks the proposed slot, types another time, or declines. Accepting confirms the meeting, schedules
reminders (the day before and an hour before) and returns a Google Meet link, a prefilled Google Calendar link and
an .ics file. Then Sorted drafts a reply to the person who asked and sends it only if the user presses Send. The
draft is a template (no LLM). "Sending" puts it in the outbox (audit log action `email_sent`): this build has no
mail server, so nothing leaves the machine, and the Meet link is a placeholder until a Google Calendar API
connection creates real ones.
"""

import hashlib
import re
from datetime import datetime, time, timedelta
from email.utils import parseaddr
from urllib.parse import urlencode

from dateutil import parser as dateparser
from sqlalchemy import select

from brain import config, db, scheduler

WHEN_HINT = re.compile(r"\d|today|tomorrow|mon|tue|wed|thu|fri|sat|sun|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
                       r"|noon", re.I)


def obligation_for(s, source_id: int) -> db.Obligation | None:
    return s.scalar(select(db.Obligation).where(db.Obligation.source_id == source_id))


def details(ob: db.Obligation) -> dict:
    """Time, person and topic, stored in the obligation note as 'HH:MM · person · topic'."""
    parts = [p.strip() for p in (ob.note or "").split(";")[0].split("·")]
    hhmm = parts[0] if parts and re.fullmatch(r"\d{1,2}:\d{2}", parts[0]) else ""
    rest = parts[1:] if hhmm else parts
    return {"time": hhmm, "person": rest[0] if rest else "", "topic": rest[1] if len(rest) > 1 else ""}


def start_of(ob: db.Obligation) -> datetime:
    hhmm = details(ob)["time"] or "09:00"
    return datetime.combine(ob.due_date, time.fromisoformat(hhmm.zfill(5)))


def title_of(ob: db.Obligation) -> str:
    d = details(ob)
    return f"{d['topic'] or 'Meeting'} with {d['person'] or ob.provider}".strip()


def slot(t: datetime) -> str:
    return f"{t:%a} {t.day} {t:%b}, {t.strftime('%I:%M %p').lstrip('0')}"


def meet_link(ob_id: int) -> str:
    """Placeholder in Meet's format, stable per meeting. A Google Calendar API connection would create a real one."""
    h = hashlib.sha256(f"sorted-meet-{ob_id}".encode()).digest()
    code = "".join("abcdefghijkmnopqrstuvwxyz"[b % 25] for b in h[:10])
    return f"https://meet.google.com/{code[:3]}-{code[3:7]}-{code[7:]}"


def google_link(title: str, start: datetime, minutes: int = 60, info: str = "") -> str:
    end = start + timedelta(minutes=minutes)
    return "https://calendar.google.com/calendar/render?" + urlencode({
        "action": "TEMPLATE", "text": title, "dates": f"{start:%Y%m%dT%H%M%S}/{end:%Y%m%dT%H%M%S}",
        "ctz": "Asia/Kolkata", "details": info})


def ics(title: str, start: datetime, uid: str, minutes: int = 60, location: str = "") -> str:
    end = start + timedelta(minutes=minutes)
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Sorted//EN", "BEGIN:VEVENT", f"UID:{uid}@sorted",
        f"DTSTAMP:{datetime.now():%Y%m%dT%H%M%S}", f"DTSTART;TZID=Asia/Kolkata:{start:%Y%m%dT%H%M%S}",
        f"DTEND;TZID=Asia/Kolkata:{end:%Y%m%dT%H%M%S}", f"SUMMARY:{title}",
        *([f"LOCATION:{location}"] * bool(location)),
        "END:VEVENT", "END:VCALENDAR", ""])


def who(ob: db.Obligation) -> str:
    d = details(ob)
    return f"{d['person']} ({ob.provider})" if d["person"] and d["person"] != ob.provider else ob.provider


def prompt(source_id: int) -> tuple[str, list[tuple[str, str]]]:
    with db.Session() as s:
        ob = obligation_for(s, source_id)
        d, start, asker = details(ob), start_of(ob), who(ob)
    text = (f"📅 Meeting request from {asker}\n"
            + (f"About: {d['topic']}\n" if d["topic"] else "")
            + f"They proposed: {slot(start)}\n\nDo you want to meet? Pick a time:")
    return text, [(f"✅ {slot(start)}", f"meet:{source_id}:yes"), ("🕐 Another time", f"meet:{source_id}:other"),
                  ("❌ Decline", f"meet:{source_id}:no")]


def parse_when(text: str, base: datetime) -> datetime | None:
    """A time the user typed ("Friday 5pm", "14 Jun 11:30", "tomorrow 10am"), resolved around the proposed slot.
    None if there is no time in it or it is in the past."""
    if not WHEN_HINT.search(text):
        return None
    now = scheduler.now()
    rel = {"today": now, "tomorrow": now + timedelta(days=1)}
    word = next((w for w in rel if w in text.lower()), None)
    default = rel[word].replace(hour=base.hour, minute=base.minute, second=0, microsecond=0) if word else base
    try:
        t = dateparser.parse(re.sub(r"today|tomorrow", "", text, flags=re.I), default=default, fuzzy=True,
                             dayfirst=True)
    except (ValueError, OverflowError):
        return None
    return t if t > now else None


def draft(source_id: int) -> dict | None:
    """The reply to the person who asked. Template text; None when there is no email address to reply to."""
    with db.Session() as s:
        ob = obligation_for(s, source_id)
        src = s.get(db.SourceRecord, source_id)
        if ob is None or src is None or src.kind != "email" or "@" not in parseaddr(src.sender)[1]:
            return None
        moved = next((a for a in s.scalars(select(db.AuditLog).where(db.AuditLog.action == "meeting_moved")
                                           .order_by(db.AuditLog.id.desc())) if a.detail.get("obligation") == ob.id),
                     None)
        d, start, status, to, subject = details(ob), start_of(ob), ob.status, src.sender, src.subject
        ob_id = ob.id
    first = (d["person"] or parseaddr(to)[0] or "there").split()[0]
    about = f" about {d['topic'].lower()}" if d["topic"] else ""
    when = f"{start:%A} {start.day} {start:%B} at {start.strftime('%I:%M %p').lstrip('0')}"
    if status == "declined":
        body = f"Thanks for getting in touch{about}. Unfortunately I can't make it, so let's skip this one for now."
    elif moved:
        body = (f"Thanks for getting in touch{about}. {moved.detail['was']} doesn't suit me, but I can do {when}.\n"
                f"Google Meet: {meet_link(ob_id)}")
    else:
        body = f"Thanks for getting in touch{about}. {when} works for me.\nGoogle Meet: {meet_link(ob_id)}"
    sign = config.env("BRAIN_USER_NAME", "")
    return {"to": to, "subject": subject if subject.lower().startswith("re:") else f"Re: {subject}",
            "body": f"Hi {first},\n\n{body}\n\nBest regards" + (f",\n{sign}" if sign else "")}


def followup(source_id: int) -> tuple[str, list[tuple[str, str]]] | None:
    m = draft(source_id)
    if m is None:
        return None
    text = f"✉️ Shall I reply?\n\nTo: {m['to']}\nSubject: {m['subject']}\n\n{m['body']}"
    return text, [("📤 Send", f"mail:{source_id}:send"), ("Don't send", f"mail:{source_id}:skip")]


def send(source_id: int, yes: bool) -> dict:
    """The user pressed Send (or not). Sending = the outbox; there is no mail server in this build."""
    m = draft(source_id)
    if m is None:
        return {"text": "There's no email address to reply to."}
    with db.Session() as s:
        if any(a.detail.get("source") == source_id for a in s.scalars(
                select(db.AuditLog).where(db.AuditLog.action.in_(("email_sent", "email_skipped"))))):
            return {"text": "Already handled that reply."}
        db.audit(s, "user", "email_sent" if yes else "email_skipped", source=source_id, **m)
        s.commit()
    if not yes:
        return {"text": f"OK, no reply sent to {m['to']}."}
    return {"text": f"📤 Sent to {m['to']} (simulated: it's in the outbox; no mail server is connected).", "sent": m}


def outbox(s) -> list[dict]:
    return [{**a.detail, "at": a.at.isoformat(timespec="minutes") if a.at else ""}
            for a in s.scalars(select(db.AuditLog).where(db.AuditLog.action == "email_sent").order_by(db.AuditLog.id))]


def decide(source_id: int, accept: bool, at: datetime | None = None) -> dict:
    """The user's answer: the proposed slot, another time (`at`), or decline.
    Returns {text, followup} plus {title, link, meet, ics} when accepted."""
    with db.Session() as s:
        ob = obligation_for(s, source_id)
        if ob is None:
            return {"text": "I couldn't find that request."}
        if ob.status in ("open", "declined"):
            return {"text": f"Already {'accepted' if ob.status == 'open' else 'declined'}: {title_of(ob)}."}
        if at is not None:
            was, d = slot(start_of(ob)), details(ob)
            ob.due_date = at.date()
            ob.note = " · ".join(filter(None, [f"{at:%H:%M}", d["person"], d["topic"]]))
            db.audit(s, "user", "meeting_moved", obligation=ob.id, was=was, to=slot(at))
        ob.status = "open" if accept else "declined"
        db.audit(s, "user", "meeting_accepted" if accept else "meeting_declined", obligation=ob.id)
        s.commit()
        ob_id, title, start, asker = ob.id, title_of(ob), start_of(ob), who(ob)
    follow = followup(source_id)
    if not accept:
        return {"text": f"Declined: {title}. I won't remind you about it.", "followup": follow}
    text = f"{title} at {start.strftime('%I:%M %p').lstrip('0')} on {start.day} {start:%b}"
    scheduler.remind_before(f"Tomorrow: {text}.", start.date(), 1, key=f"meet:{ob_id}:1d", obligation_id=ob_id)
    if start - timedelta(hours=1) > scheduler.now():
        scheduler.create_reminder(f"In 1 hour: {text}.", start - timedelta(hours=1), key=f"meet:{ob_id}:1h",
                                  obligation_id=ob_id)
    meet = meet_link(ob_id)
    link = google_link(title, start, info=f"Requested by {asker}. Google Meet: {meet}")
    return {"title": title, "link": link, "meet": meet, "ics": ics(title, start, f"meet{ob_id}", location=meet),
            "followup": follow,
            "text": (f"✅ Booked: {title}\n{slot(start)}\nGoogle Meet: {meet} (placeholder link)\n"
                     "I'll remind you the day before and an hour before.")}

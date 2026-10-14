"""IMAP email adapter (Gmail / iCloud / Outlook with an app-specific password). Read-only: messages are
fetched with BODY.PEEK and the mailbox is opened read-only, so nothing is marked read, moved or deleted."""

import imaplib
from datetime import date

from brain import config
from brain.messages import Message, from_eml


def fetch(since: date | None = None, folder: str = "INBOX", limit: int = 100) -> list[Message]:
    host = config.env("IMAP_HOST", "imap.gmail.com")
    user, password = config.env("IMAP_USER"), config.env("IMAP_PASSWORD")
    if not (user and password):
        raise RuntimeError("set IMAP_USER and IMAP_PASSWORD (an app password) in .env")
    out = []
    with imaplib.IMAP4_SSL(host) as box:
        box.login(user, password)
        box.select(folder, readonly=True)
        _, data = box.uid("search", None, f'(SINCE "{since:%d-%b-%Y}")' if since else "ALL")
        for uid in data[0].split()[-limit:]:
            _, parts = box.uid("fetch", uid, "(BODY.PEEK[])")
            out.append(from_eml(parts[0][1], f"imap:{folder}/{uid.decode()}"))
    return out

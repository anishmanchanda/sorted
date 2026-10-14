"""The only outbound channel: messages to the user themself. No tool exists to message anyone else."""

from collections.abc import Callable

from brain import db

SINKS: list[Callable[[str], None]] = []  # e.g. the Telegram bot registers one; the demo prints


def send_self(text: str) -> None:
    with db.Session() as s:
        db.audit(s, "notify", "send_self", text=text)
        s.commit()
    for sink in SINKS:
        sink(text)

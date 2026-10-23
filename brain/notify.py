"""Messages to the user themself. No agent can message anyone else; the only reply to another person is the
meeting reply in brain.meetings, sent only on the user's button press (to an outbox)."""

from collections.abc import Callable

from brain import db

SINKS: list[Callable[[str], None]] = []  # e.g. the Telegram bot registers one; the demo prints
# prompts with buttons: (text, [(label, action_id)]); action ids are handled by brain.actions
ASK_SINKS: list[Callable[[str, list[tuple[str, str]]], None]] = []


def send_self(text: str) -> None:
    with db.Session() as s:
        db.audit(s, "notify", "send_self", text=text)
        s.commit()
    for sink in SINKS:
        sink(text)


def ask_self(text: str, actions: list[tuple[str, str]]) -> None:
    """A question to the user with buttons. Without a button-capable channel it degrades to plain text."""
    with db.Session() as s:
        db.audit(s, "notify", "ask_self", text=text, actions=[a for _, a in actions])
        s.commit()
    if ASK_SINKS:
        for sink in ASK_SINKS:
            sink(text, actions)
    else:
        for sink in SINKS:
            sink(text + "\n" + "  ".join(f"[{label}]" for label, _ in actions))

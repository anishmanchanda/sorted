"""Default source for the demo and tests: the synthetic inbox in data/samples/."""

import json
from datetime import datetime
from pathlib import Path

from brain import config
from brain.messages import Message, from_eml, to_ist_naive
from brain.sources.pdf import from_pdf


def _rel(p: Path) -> str:
    return str(p.relative_to(config.ROOT)) if p.is_relative_to(config.ROOT) else str(p)


def load_fixtures(root: Path = config.SAMPLES_DIR) -> list[Message]:
    msgs = [from_eml(p.read_bytes(), _rel(p)) for p in sorted((root / "email").glob("*.eml"))]
    sms_file = root / "sms" / "sms.jsonl"
    for line in sms_file.read_text().splitlines():
        r = json.loads(line)
        msgs.append(Message("sms", r["sender"], "", r["body"], to_ist_naive(datetime.fromisoformat(r["received_at"])),
                            f"{_rel(sms_file)}#{r['id']}"))
    msgs += [from_pdf(p, _rel(p)) for p in sorted((root / "pdf").glob("*.pdf"))]
    return sorted(msgs, key=lambda m: m.received_at)

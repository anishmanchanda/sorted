"""Field-extraction accuracy per handler (LLM vs compiled ability), written to reports/eval.md.

Predictions are the `extract` traces already in the DB (written by `make demo` / the orchestrator),
so eval never spends tokens itself. Each trace's source_records.raw_path identifies the sample:
`data/samples/email/<id>.eml`, `data/samples/pdf/<id>.pdf` or `data/samples/sms/sms.jsonl#<id>`.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from brain import config, db

FIELDS = ("type", "provider", "amount", "due_date")
_STOP = {"bank", "ltd", "limited", "india", "of", "the", "co", "company", "insurance", "power", "govt"}


def load_labels() -> dict[str, dict]:
    with open(config.LABELS_PATH) as f:
        return {(row := json.loads(line))["id"]: row for line in f if line.strip()}


def sample_id(raw_path: str) -> str:
    return raw_path.rsplit("#", 1)[1] if "#" in raw_path else Path(raw_path).stem


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def provider_match(pred: str | None, gold: str | None) -> bool:
    if not pred or not gold:
        return pred == gold
    p, g = " ".join(sorted(_tokens(pred))), " ".join(sorted(_tokens(gold)))
    return p in g or g in p or bool((_tokens(pred) & _tokens(gold)) - _STOP)


def score_one(pred: dict, gold: dict) -> dict[str, bool]:
    """Which fields the prediction got right. `ignore` samples are scored on type only."""
    out = {"type": pred.get("type") == gold["type"]}
    if gold["type"] == "ignore":
        return out
    amount = pred.get("amount")
    out["provider"] = provider_match(pred.get("provider"), gold["provider"])
    out["amount"] = (amount is None and gold["amount"] is None) or (
        amount is not None and gold["amount"] is not None and abs(float(amount) - gold["amount"]) < 0.01
    )
    out["due_date"] = (pred.get("due_date") or None) == gold["due_date"]
    return out


def handler_group(handler: str) -> str:
    return "llm" if handler == "llm" else "compiled"


def evaluate(rows: list[tuple[str, str, dict]], labels: dict[str, dict]) -> dict[str, dict[str, list[bool]]]:
    """rows = (handler, sample_id, prediction). Returns {handler_or_group: {field: [hits]}}."""
    res: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for handler, sid, pred in rows:
        if sid not in labels:
            continue
        for field, ok in score_one(pred, labels[sid]).items():
            for key in dict.fromkeys((handler, handler_group(handler), "all")):
                res[key][field].append(ok)
    return res


def _pct(hits: list[bool]) -> str:
    return f"{100 * sum(hits) / len(hits):.1f}% ({sum(hits)}/{len(hits)})" if hits else "-"


def render(res, labels) -> str:
    kinds = defaultdict(int)
    for lab in labels.values():
        kinds[f"{lab['kind']}/{lab['type']}"] += 1
    lines = ["# Extraction eval", "", f"Labelled samples: {len(labels)} (`data/eval/labels.jsonl`)", ""]
    if not res:
        lines += ["No `extract` traces in the DB yet. Run `make demo` first, then `make eval`.", ""]
    else:
        lines += ["| handler | " + " | ".join(FIELDS) + " |", "|---" * (len(FIELDS) + 1) + "|"]
        order = ["all", "llm", "compiled"] + sorted(k for k in res if k not in ("all", "llm", "compiled"))
        for key in (k for k in order if k in res):
            lines.append(f"| {key} | " + " | ".join(_pct(res[key].get(f, [])) for f in FIELDS) + " |")
        lines.append("")
    lines += ["## Dataset", "", "| kind/type | n |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in sorted(kinds.items())]
    return "\n".join(lines) + "\n"


def run() -> str:
    db.init_db()
    labels = load_labels()
    with db.Session() as s:
        q = (
            select(db.Trace.handler, db.SourceRecord.raw_path, db.Trace.output_json)
            .join(db.SourceRecord, db.Trace.input_ref == db.SourceRecord.id)
            .where(db.Trace.task_kind == "extract")
        )
        rows = [(h, sample_id(p), out) for h, p, out in s.execute(q)]
    report = render(evaluate(rows, labels), labels)
    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "eval.md").write_text(report)
    return report


if __name__ == "__main__":
    print(run())

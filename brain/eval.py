"""Field-extraction accuracy per handler (LLM vs compiled ability), written to reports/eval.md.

Predictions are the `extract` traces already in the DB (written by `make demo` / the orchestrator),
so eval never spends tokens itself. Each trace's source_records.raw_path identifies the sample:
`data/samples/email/<id>.eml`, `data/samples/pdf/<id>.pdf` or `data/samples/sms/sms.jsonl#<id>`.
"""

import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from brain import config, db
from brain.state import provider_match

FIELDS = ("type", "provider", "amount", "due_date")


def load_labels() -> dict[str, dict]:
    with open(config.LABELS_PATH) as f:
        return {(row := json.loads(line))["id"]: row for line in f if line.strip()}


def sample_id(raw_path: str) -> str:
    return raw_path.rsplit("#", 1)[1] if "#" in raw_path else Path(raw_path).stem


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
    """llm / compiled (ability:<name>@v<n>) / rule (rule:<name>) / ml (local classifier)."""
    return {"ability": "compiled", "rule": "rule", "ml": "ml"}.get(handler.split(":")[0], "llm")


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
        groups = ("all", "llm", "compiled", "ml", "rule")
        order = list(groups) + sorted(k for k in res if k not in groups)
        for key in (k for k in order if k in res):
            lines.append(f"| {key} | " + " | ".join(_pct(res[key].get(f, [])) for f in FIELDS) + " |")
        lines.append("")
    lines += ["## Dataset", "", "| kind/type | n |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in sorted(kinds.items())]
    return "\n".join(lines) + "\n"


def classifier_section(seeds=(1, 2, 3, 7, 11)) -> str:
    """Held-out accuracy of the local TF-IDF + LogisticRegression classifier (stratified 70/30 splits)."""
    from brain.ml.classifier import threshold
    from brain.ml.train import held_out_report

    reps = [held_out_report(seed) for seed in seeds]
    mean = lambda k: 100 * sum(r[k] for r in reps) / len(reps)  # noqa: E731
    lines = ["", "## Local classifier (scikit-learn, held-out)", "",
             f"{len(seeds)} stratified 70/30 splits of the labelled non-OTP samples "
             f"({reps[0]['test']} unseen per split).",
             "", "| metric | mean over splits |", "|---|---|",
             f"| accuracy (all predictions) | {mean('accuracy'):.1f}% |",
             f"| share with confidence >= {threshold()} (decided locally if `ignore`) | "
             f"{mean('confident_share'):.1f}% |",
             f"| accuracy of those confident predictions | {mean('confident_accuracy'):.1f}% |", ""]
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
    report = render(evaluate(rows, labels), labels) + classifier_section()
    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "eval.md").write_text(report)
    return report


if __name__ == "__main__":
    print(run())

"""Train the local classifier: `python -m brain.ml.train`.

Training data = the hand-labelled samples (data/eval/labels.jsonl) + every accepted LLM-labelled message in
the DB. `held_out_report()` measures accuracy on a stratified 30% split that the model never saw.
"""

from collections import Counter

from sklearn.model_selection import train_test_split
from sqlalchemy import select

from brain import db
from brain.eval import load_labels, sample_id
from brain.ml.classifier import EmailClassifier, Example, set_current, threshold


def labelled_examples() -> list[Example]:
    from brain.sources.fixtures import load_fixtures

    labels = load_labels()
    return [Example(m.kind, m.sender, m.subject, m.redacted_text(), labels[sample_id(m.raw_path)]["type"])
            for m in load_fixtures() if not labels[sample_id(m.raw_path)].get("otp")]  # OTPs never reach it


def trace_examples() -> list[Example]:
    """Messages the LLM labelled (accepted extract traces)."""
    with db.Session() as s:
        rows = s.execute(select(db.SourceRecord, db.Trace.output_json)
                         .join(db.Trace, db.Trace.input_ref == db.SourceRecord.id)
                         .where(db.Trace.task_kind == "extract", db.Trace.handler == "llm",
                                db.Trace.accepted.is_(True))).all()
    return [Example(src.kind, src.sender, src.subject, src.text, out["type"]) for src, out in rows]


def train(examples: list[Example], save: bool = True) -> EmailClassifier:
    seen, unique = set(), []
    for ex in examples:  # the same message can be both a labelled sample and an LLM trace
        if ex.text not in seen:
            seen.add(ex.text)
            unique.append(ex)
    clf = EmailClassifier().fit(unique)
    if save:
        clf.save()
    set_current(clf)
    return clf


def held_out_report(seed: int = 7) -> dict:
    exs = labelled_examples()
    counts = Counter(e.label for e in exs)
    singles = [e for e in exs if counts[e.label] < 2]  # a class seen once can only be trained on
    rest = [e for e in exs if counts[e.label] >= 2]
    train_ex, test_ex = train_test_split(rest, test_size=0.3, random_state=seed, stratify=[e.label for e in rest])
    train_ex += singles
    clf = EmailClassifier().fit(train_ex)
    rows = [(clf.predict(e.kind, e.sender, e.subject, e.text), e.label) for e in test_ex]
    confident = [(p, gold) for p, gold in rows if p[1] >= threshold()]
    return {
        "train": len(train_ex), "test": len(test_ex),
        "accuracy": sum(p[0] == gold for p, gold in rows) / len(rows),
        "by_layer": dict(Counter(p[2] for p, _ in rows)),
        "confident_share": len(confident) / len(rows),
        "confident_accuracy": sum(p[0] == gold for p, gold in confident) / len(confident) if confident else 0.0,
        "errors": [(e.subject or e.sender, p[0], e.label) for (p, _), e in zip(rows, test_ex, strict=True)
                   if p[0] != e.label],
    }


if __name__ == "__main__":
    db.init_db()
    clf = train(labelled_examples() + trace_examples())
    print(f"trained on {clf.n_examples} examples, {len(clf.rules)} sender rules -> saved")
    r = held_out_report()
    print(f"held-out: {100 * r['accuracy']:.1f}% on {r['test']} unseen samples (layers {r['by_layer']}); "
          f"{100 * r['confident_share']:.0f}% above threshold {threshold()} at {100 * r['confident_accuracy']:.1f}%")

"""Two-layer email-type classifier.

Layer 1, exact rules: for a known sender, the subject words common to all of its examples of one type
(e.g. account.netflix.com + {netflix, payment, receipt} -> subscription_receipt). One unambiguous hit wins.
Layer 2, TF-IDF + LogisticRegression over the redacted text, for unknown senders and ambiguous cases.

The orchestrator only acts locally on a confident `ignore` (promotions, newsletters): it skips the LLM.
Anything below BRAIN_CLASSIFIER_THRESHOLD goes to the LLM, whose label becomes new training data.
"""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from brain import config
from brain.compiler.detector import subject_words
from brain.messages import sender_key

MODEL_PATH = Path(config.env("BRAIN_MODEL_DIR", str(config.ROOT / "data" / "models"))) / "classifier.joblib"


@dataclass
class Example:
    kind: str
    sender: str
    subject: str
    text: str  # redacted text, as stored in source_records.text
    label: str


def _words(subject: str, text: str) -> set[str]:
    """Rule signature: subject words, or the body's words for SMS/PDF that have no subject."""
    return subject_words(subject or text)


class EmailClassifier:
    def __init__(self):
        self.rules: dict[tuple[str, str], set[str]] = {}
        self.model = None
        self.n_examples = 0

    def fit(self, examples: list[Example]) -> "EmailClassifier":
        self.n_examples = len(examples)
        groups = defaultdict(list)
        for ex in examples:
            groups[(sender_key(ex.kind, ex.sender), ex.label)].append(_words(ex.subject, ex.text))
        self.rules = {k: set.intersection(*ws) for k, ws in groups.items() if len(ws) >= 2}
        if len({ex.label for ex in examples}) >= 2:
            self.model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
                                       LogisticRegression(C=10, max_iter=2000))
            self.model.fit([ex.text for ex in examples], [ex.label for ex in examples])
        return self

    def predict(self, kind: str, sender: str, subject: str, text: str) -> tuple[str | None, float, str]:
        """(label, confidence, layer) with layer in rule / tfidf / none."""
        key, words = sender_key(kind, sender), _words(subject, text)
        hits = {label for (sk, label), kw in self.rules.items() if sk == key and kw <= words}
        if len(hits) == 1:
            return hits.pop(), 1.0, "rule"
        if self.model is None:
            return None, 0.0, "none"
        proba = self.model.predict_proba([text])[0]
        best = proba.argmax()
        return str(self.model.classes_[best]), float(proba[best]), "tfidf"

    def save(self, path=MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)


_current: EmailClassifier | None = None


def current() -> EmailClassifier | None:
    """The trained model if one exists (cached per process)."""
    global _current
    if _current is None and MODEL_PATH.exists():
        _current = joblib.load(MODEL_PATH)
    return _current


def set_current(clf: EmailClassifier | None) -> None:
    global _current
    _current = clf


def threshold() -> float:
    return float(config.env("BRAIN_CLASSIFIER_THRESHOLD", "0.7"))

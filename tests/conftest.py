import os

# Tests never touch the real DB file, never hit a live LLM, and never use a replay cache.
os.environ["BRAIN_DB_URL"] = "sqlite://"
os.environ["BRAIN_LLM_CACHE"] = ""
os.environ["BRAIN_MODEL_DIR"] = __import__("tempfile").mkdtemp(prefix="sorted-models-")
os.environ["BRAIN_ABILITIES_DIR"] = __import__("tempfile").mkdtemp(prefix="sorted-abilities-")

import pytest  # noqa: E402

from brain import db  # noqa: E402
from brain.eval import load_labels, sample_id  # noqa: E402
from brain.llm import LLMResult  # noqa: E402
from brain.sources.fixtures import load_fixtures  # noqa: E402
from brain.validate import Extraction  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    from brain.ml import classifier

    db.Base.metadata.drop_all(db.engine)
    db.init_db()
    classifier.set_current(None)
    yield
    classifier.set_current(None)


class FakeLLM:
    """Stands in for brain.llm.LLM. `answer(user_text, schema) -> dict`."""

    def __init__(self, answer):
        self.answer = answer
        self.calls: list[str] = []

    def json(self, route, system, user, schema, run_id=""):
        self.calls.append(user)
        return LLMResult(schema.model_validate(self.answer(user, schema)), 100, 0.0001, "fake")


@pytest.fixture
def make_llm():
    return FakeLLM


@pytest.fixture(scope="session")
def fixtures():
    return load_fixtures()


@pytest.fixture
def label_llm(fixtures):
    """A perfect extractor: answers with the ground-truth label of whichever fixture is in the prompt."""
    labels = load_labels()
    table = [(m.redacted_text(), labels[sample_id(m.raw_path)]) for m in fixtures]

    def answer(user, schema):
        for text, lab in table:
            if text in user:
                return {k: v for k, v in lab.items() if k in Extraction.model_fields}
        raise KeyError("prompt does not contain a known fixture")

    return FakeLLM(answer)

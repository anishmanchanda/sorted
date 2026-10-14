from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from brain.llm import LLM, BudgetExceeded, LLMUnavailable, parse_prices


class Out(BaseModel):
    amount: float


class FakeClient:
    def __init__(self, contents):
        self.contents = list(contents)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.requests.append(kw)
        usage = SimpleNamespace(total_tokens=30, prompt_tokens=20, completion_tokens=10)
        msg = SimpleNamespace(content=self.contents.pop(0))
        return SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=msg)])


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "c")
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    monkeypatch.setenv("BRAIN_SMALL_PROVIDER", "cerebras")
    monkeypatch.setenv("BRAIN_SMALL_MODEL", "small-m")
    monkeypatch.setenv("BRAIN_STRONG_PROVIDER", "openai")
    monkeypatch.setenv("BRAIN_STRONG_MODEL", "strong-m")
    monkeypatch.setenv("BRAIN_OPENAI_FALLBACK_MODEL", "openai-fallback")
    monkeypatch.setenv("BRAIN_CEREBRAS_FALLBACK_MODEL", "cerebras-fallback")


def test_routes_and_fallback(keys, monkeypatch):
    llm = LLM()
    assert llm.route("small") == ("cerebras", "small-m")
    assert llm.route("strong") == ("openai", "strong-m")
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    assert llm.route("small") == ("openai", "openai-fallback")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(LLMUnavailable):
        llm.route("small")


def test_retry_once_with_validation_error_and_redaction(keys):
    llm = LLM()
    client = FakeClient(['{"amount": "lots"}', '{"amount": 12.5}'])
    llm._clients["cerebras"] = client
    res = llm.json("small", "sys", "card 4111 1111 1111 4821", Out, run_id="r1")
    assert res.data.amount == 12.5 and res.tokens == 60
    assert "4111" not in client.requests[0]["messages"][1]["content"]
    assert "failed validation" in client.requests[1]["messages"][-1]["content"]
    assert client.requests[0]["response_format"] == {"type": "json_object"}


def test_cost_and_budget(keys, monkeypatch):
    monkeypatch.setenv("BRAIN_PRICES", "small-m=1/2")
    monkeypatch.setenv("BRAIN_RUN_TOKEN_BUDGET", "50")
    llm = LLM()
    llm._clients["cerebras"] = FakeClient(['{"amount": 1}', '{"amount": 2}'])
    res = llm.json("small", "s", "u1", Out, run_id="r")
    assert res.cost == pytest.approx((20 * 1 + 10 * 2) / 1e6)
    llm.json("small", "s", "u2", Out, run_id="r")  # 30 tokens used, still under 50
    with pytest.raises(BudgetExceeded):
        llm.json("small", "s", "u3", Out, run_id="r")
    assert parse_prices("a=0.5/1, b=2/8") == {"a": (0.5, 1.0), "b": (2.0, 8.0)}


def test_record_and_replay(keys, tmp_path, monkeypatch):
    llm = LLM(cache_dir=tmp_path)
    llm._clients["cerebras"] = FakeClient(['{"amount": 7}'])
    assert not llm.json("small", "s", "u", Out).replayed
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    again = LLM(cache_dir=tmp_path).json("small", "s", "u", Out)  # no keys needed
    assert again.replayed and again.data.amount == 7 and again.tokens == 30

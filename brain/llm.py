"""LLM wrapper: two routes (small / strong), OpenAI SDK for both OpenAI and Cerebras (OpenAI-compatible),
JSON output validated by Pydantic with one repair retry, token budgets, cost accounting, and an optional
record/replay cache (BRAIN_LLM_CACHE) so a recorded demo can be replayed without API keys.

Every prompt's user content is redacted here, so no caller can forget to.
"""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select

from brain import config, db
from brain.redact import redact

BASE_URLS = {"openai": None, "cerebras": "https://api.cerebras.ai/v1"}


class LLMUnavailable(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class LLMResult:
    data: BaseModel
    tokens: int
    cost: float  # USD, estimated from BRAIN_PRICES
    model: str
    replayed: bool = False


def parse_prices(spec: str) -> dict[str, tuple[float, float]]:
    """'gpt-oss-120b=0.35/0.75,gpt-5.4=2.5/15' -> {model: (usd_per_1M_in, usd_per_1M_out)}"""
    out = {}
    for item in filter(None, (x.strip() for x in spec.split(","))):
        name, _, pair = item.partition("=")
        i, _, o = pair.partition("/")
        out[name.strip()] = (float(i), float(o))
    return out


class LLM:
    def __init__(self, cache_dir: str | Path | None = None):
        cache = cache_dir or config.env("BRAIN_LLM_CACHE")
        self.cache_dir = Path(cache) if cache else None
        self.prices = parse_prices(config.env("BRAIN_PRICES"))
        self.run_budget = int(config.env("BRAIN_RUN_TOKEN_BUDGET", "20000"))
        self.day_budget = int(config.env("BRAIN_DAY_TOKEN_BUDGET", "500000"))
        self.run_tokens: dict[str, int] = defaultdict(int)
        self._day: tuple[date, int] | None = None
        self._clients: dict[str, OpenAI] = {}

    def route(self, route: str) -> tuple[str, str]:
        """(provider, model) for 'small' or 'strong'. Falls back to the other provider if a key is missing."""
        r = route.upper()
        provider = config.env(f"BRAIN_{r}_PROVIDER", "cerebras" if route == "small" else "openai")
        model = config.env(f"BRAIN_{r}_MODEL")
        if not config.env(f"{provider.upper()}_API_KEY"):
            other = "openai" if provider == "cerebras" else "cerebras"
            if not config.env(f"{other.upper()}_API_KEY"):
                raise LLMUnavailable("set OPENAI_API_KEY and/or CEREBRAS_API_KEY")
            provider, model = other, config.env(f"BRAIN_{other.upper()}_FALLBACK_MODEL")
        if not model:
            raise LLMUnavailable(f"no model configured for route {route!r} (see .env.example)")
        return provider, model

    def _client(self, provider: str) -> OpenAI:
        if provider not in self._clients:
            self._clients[provider] = OpenAI(api_key=config.env(f"{provider.upper()}_API_KEY"),
                                             base_url=BASE_URLS[provider], max_retries=3)
        return self._clients[provider]

    def _day_used(self) -> int:
        today = date.today()
        if not self._day or self._day[0] != today:
            with db.Session() as s:
                used = s.scalar(select(func.coalesce(func.sum(db.Trace.tokens), 0))
                                .where(db.Trace.created_at >= datetime.combine(today, datetime.min.time())))
            self._day = (today, int(used or 0))
        return self._day[1]

    def _spend(self, run_id: str, tokens: int) -> None:
        self.run_tokens[run_id] += tokens
        self._day_used()
        self._day = (self._day[0], self._day[1] + tokens)

    def cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        p_in, p_out = self.prices.get(model, (0.0, 0.0))
        return (prompt_tokens * p_in + completion_tokens * p_out) / 1e6

    def json(self, route: str, system: str, user: str, schema: type[BaseModel], run_id: str = "") -> LLMResult:
        user = redact(user)
        key = hashlib.sha256(json.dumps([route, system, user, schema.__name__]).encode()).hexdigest()
        cached = self.cache_dir / f"{key}.json" if self.cache_dir else None
        if cached and cached.exists():
            rec = json.loads(cached.read_text())
            return LLMResult(schema.model_validate(rec["data"]), rec["tokens"], rec["cost"], rec["model"], True)

        if self.run_tokens[run_id] >= self.run_budget:
            raise BudgetExceeded(f"run {run_id} used {self.run_tokens[run_id]} tokens (budget {self.run_budget})")
        if self._day_used() >= self.day_budget:
            raise BudgetExceeded(f"daily token budget {self.day_budget} reached")

        provider, model = self.route(route)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        tokens, cost = 0, 0.0
        for attempt in range(2):
            resp = self._client(provider).chat.completions.create(
                model=model, messages=messages, response_format={"type": "json_object"})
            usage = resp.usage
            tokens += usage.total_tokens
            cost += self.cost(model, usage.prompt_tokens, usage.completion_tokens)
            content = resp.choices[0].message.content or ""
            try:
                data = schema.model_validate_json(content)
                break
            except ValidationError as e:
                if attempt:
                    self._spend(run_id, tokens)
                    raise
                fix = f"That JSON failed validation:\n{e}\nReturn corrected JSON only."
                messages += [{"role": "assistant", "content": content}, {"role": "user", "content": fix}]
        self._spend(run_id, tokens)
        if cached:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps({"data": data.model_dump(mode="json"), "tokens": tokens, "cost": cost,
                                          "model": model}, indent=1))
        return LLMResult(data, tokens, cost, model)

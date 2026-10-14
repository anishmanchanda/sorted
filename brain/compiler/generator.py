"""Compiler agent: writes a deterministic parser from accepted traces (strong LLM route), then static check
and sandbox tests against visible and held-out cases. One retry with the failures fed back."""

import inspect
import json
import random
import uuid
from pathlib import Path

import openai
from pydantic import BaseModel
from sqlalchemy import delete

from brain import config, db
from brain.compiler import detector, sandbox, static_check
from brain.llm import LLM, BudgetExceeded, LLMUnavailable
from brain.state import provider_match
from brain.validate import Extraction

HELD_OUT_SHARE = 0.3
HELD_OUT_PASS = 0.98
FIELD_ORDER = list(Extraction.model_fields)

COMPILER_SYSTEM = """You are the compiler agent of Sorted. You turn repeated LLM extractions into a small,
deterministic Python parser that will run locally with no LLM.

Write Python source that defines:
    def extract(text: str) -> dict
It receives the full message text (From/Subject/Date headers + body, already redacted) and must return a dict
with exactly the keys in OUTPUT_FIELDS, in the same formats as the examples: amounts as float, dates as
"YYYY-MM-DD" strings, times as "HH:MM", and fields that never change across examples (type, provider,
currency, service, person ...) as the literal values from the examples.

Rules:
- Pure function: no network, files, subprocess, eval/exec/open, no dunder attributes, no global/nonlocal.
- Imports allowed ONLY: re, datetime, decimal, html, json, dateutil (e.g. dateutil.parser). Nothing else.
- Generalise: amounts, dates and months change in every message; the layout stays. Anchor regexes on the
  labels around each value; tolerate extra whitespace and Indian digit grouping (1,23,456.78).
- If a required label is missing (the layout changed), raise ValueError. Never guess or return defaults.
- Do not define TRIGGER, PERMISSIONS or OUTPUT_FIELDS; they are added for you.
Return JSON: {"code": "<python source>", "notes": "<one line>"}"""

HEADER = '''"""Ability {name} v{version}: compiled by Sorted from {n} accepted LLM traces.
Generated code: no LLM calls, no I/O. Passed brain.compiler.static_check and sandbox tests before use.
Output is validated against the Pydantic schema brain.validate.Extraction on every run."""

TRIGGER = {trigger!r}
PERMISSIONS = ["read:message_text"]
OUTPUT_FIELDS = {fields!r}

'''


class CodeGen(BaseModel):
    code: str
    notes: str = ""


def compare(expected: dict, got) -> list[str]:
    """Fields where `got` disagrees with `expected` (numbers within 0.01, strings case-insensitive)."""
    if not isinstance(got, dict):
        return ["<not a dict>"]
    bad = []
    for key, want in expected.items():
        have = got.get(key)
        if key in ("provider", "service"):
            ok = isinstance(have, str) and provider_match(have, want)
        elif isinstance(want, (int, float)) and not isinstance(want, bool):
            ok = isinstance(have, (int, float)) and not isinstance(have, bool) and abs(have - want) < 0.01
        elif isinstance(want, str):
            ok = isinstance(have, str) and have.strip().lower() == want.strip().lower()
        else:
            ok = have == want
        if not ok:
            bad.append(key)
    return bad


def split_cases(ability: db.Ability, items) -> list[dict]:
    cases = [{"input": src.text, "expected": t.output_json, "source_id": src.id, "held_out": False}
             for t, src in items]
    must_show = {i for i, c in enumerate(cases)
                 if ability.repair_from_source and c["source_id"] >= ability.repair_from_source}
    pool = [i for i in range(len(cases)) if i not in must_show]
    n_held = round(len(cases) * HELD_OUT_SHARE) if len(cases) >= 3 else 0
    n_held = max(0, min(n_held, len(pool) - (0 if must_show else 1)))
    for i in random.Random(f"{ability.name}@{ability.version}").sample(pool, n_held):
        cases[i]["held_out"] = True
    return cases


def _prompt(ability, fields, visible) -> str:
    parts = [f"ABILITY: {ability.name}", f"OUTPUT_FIELDS: {fields}", "", "EXAMPLES (input -> expected output):"]
    for i, c in enumerate(visible, 1):
        parts += [f"--- example {i} ---", "INPUT:", c["input"], "EXPECTED:", json.dumps(c["expected"])]
    return "\n".join(parts)


TEST_TEMPLATE = '''"""Generated from accepted traces. Cases with held_out=true were never shown to the compiler."""

import importlib.util
import json
import pathlib
import re

import pytest

HERE = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location("ability", HERE / "ability.py")
ability = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ability)
CASES = json.loads((HERE / "cases.json").read_text())


def provider_match(a, b):
    ta, tb = set(re.findall(r"[a-z0-9]+", a.lower())), set(re.findall(r"[a-z0-9]+", b.lower()))
    return ta <= tb or tb <= ta or bool((ta & tb) - {"bank", "ltd", "limited", "india", "of", "the"})


{compare}

@pytest.mark.parametrize("case", CASES, ids=[f"{i}{'-heldout' if c['held_out'] else ''}" for i, c in enumerate(CASES)])
def test_case(case):
    assert compare(case["expected"], ability.extract(case["input"])) == []
'''


def export(ability: db.Ability, cases: list[dict]) -> None:
    """Write the ability, its cases and a standalone pytest file to abilities/<name>/v<n>/ for humans."""
    d = Path(config.env("BRAIN_ABILITIES_DIR", str(config.ROOT / "abilities"))) / ability.name / f"v{ability.version}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "ability.py").write_text(ability.code)
    (d / "cases.json").write_text(json.dumps(
        [{k: c[k] for k in ("input", "expected", "held_out")} for c in cases], indent=1, ensure_ascii=False))
    (d / "test_ability.py").write_text(TEST_TEMPLATE.replace("{compare}", inspect.getsource(compare)))


def compile_ability(s, ability: db.Ability, llm: LLM) -> dict:
    items = detector.items_for(s, ability)
    cases = split_cases(ability, items)
    s.execute(delete(db.AbilityTest).where(db.AbilityTest.ability_id == ability.id))
    s.add_all(db.AbilityTest(ability_id=ability.id, input=c["input"], expected_output=c["expected"],
                             held_out=c["held_out"]) for c in cases)
    visible = [c for c in cases if not c["held_out"]]
    held = [c for c in cases if c["held_out"]]
    fields = [f for f in FIELD_ORDER if any(f in c["expected"] for c in visible)]
    base_prompt = _prompt(ability, fields, visible)
    run_id, tokens, cost, feedback, prev, held_rate = uuid.uuid4().hex[:12], 0, 0.0, "", "", 0.0

    for _attempt in range(2):
        prompt = base_prompt + (f"\n\nYOUR PREVIOUS CODE:\n{prev}\n\nPROBLEMS:\n{feedback}\n"
                                "Return the full corrected code." if feedback else "")
        try:
            res = llm.json("strong", COMPILER_SYSTEM, prompt, CodeGen, run_id)
        except (BudgetExceeded, LLMUnavailable, openai.APIError) as e:
            feedback = f"compiler LLM unavailable: {e}"
            break
        tokens, cost, prev = tokens + res.tokens, cost + res.cost, res.data.code
        code = HEADER.format(name=ability.name, version=ability.version, n=len(items), fields=fields,
                             trigger={k: v for k, v in ability.trigger_json.items() if k != "n_traces"}) + prev
        problems = static_check.check(code)
        if problems:
            feedback = "Static check rejected the code:\n" + "\n".join(problems)
            continue
        ability.code, ability.status = code, "generated"
        results = sandbox.run(code, [c["input"] for c in cases])
        failures, held_failed = [], 0
        for c, r in zip(cases, results, strict=True):
            bad = compare(c["expected"], r["value"]) if r["ok"] else [r["error"]]
            if bad and c["held_out"]:
                held_failed += 1
            elif bad:
                got = r["value"] if r["ok"] else r["error"]
                failures.append(f"example {visible.index(c) + 1}: expected {json.dumps(c['expected'])} "
                                f"got {json.dumps(got, default=str)} (wrong: {bad})")
        held_rate = 1 - held_failed / len(held) if held else 1.0
        if not failures and held_rate >= HELD_OUT_PASS:
            ability.status = "tested"
            break
        feedback = "\n".join(failures) + (
            f"\n{held_failed} of {len(held)} held-out cases (not shown to you) also failed; generalise."
            if held_failed else "")
    if ability.status != "tested":
        ability.status, ability.last_error = "candidate", feedback[:2000]
    else:
        ability.last_error = ""
        export(ability, cases)
    ability.trigger_json = {**ability.trigger_json, "n_traces": len(items)}
    s.add(db.Trace(run_id=run_id, task_kind="compile", handler="llm", tokens=tokens, cost=cost,
                   input_ref=items[-1][1].id if items else None, accepted=ability.status == "tested",
                   output_json={"ability": ability.name, "version": ability.version, "status": ability.status,
                                "visible": len(visible), "held_out": len(held), "held_out_pass_rate": held_rate}))
    db.audit(s, "compiler", "compiled", ability=ability.name, version=ability.version, status=ability.status)
    return {"ability": ability.name, "version": ability.version, "status": ability.status, "visible": len(visible),
            "held_out": len(held), "held_out_pass_rate": held_rate, "tokens": tokens, "error": ability.last_error}


def compile_pending(s, llm: LLM) -> list[dict]:
    return [compile_ability(s, ab, llm) for ab in detector.scan(s)]

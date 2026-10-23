"""Generated from accepted traces. Cases with held_out=true were never shown to the compiler."""

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


def compare(expected: dict, got) -> list[str]:
    """Fields where `got` disagrees with `expected` (numbers within 0.01, strings case-insensitive)."""
    if not isinstance(got, dict):
        return ["<not a dict>"]
    bad = []
    for key, want in expected.items():
        have = got.get(key)
        if key in ("provider", "service"):
            ok = isinstance(have, str) and provider_match(have, want)
        elif key == "topic":  # the LLM's own few-word summary, not a fact in the text: any non-empty string
            ok = isinstance(have, str) and bool(have.strip())
        elif isinstance(want, (int, float)) and not isinstance(want, bool):
            ok = isinstance(have, (int, float)) and not isinstance(have, bool) and abs(have - want) < 0.01
        elif isinstance(want, str):
            ok = isinstance(have, str) and have.strip().lower() == want.strip().lower()
        else:
            ok = have == want
        if not ok:
            bad.append(key)
    return bad


@pytest.mark.parametrize("case", CASES, ids=[f"{i}{'-heldout' if c['held_out'] else ''}" for i, c in enumerate(CASES)])
def test_case(case):
    assert compare(case["expected"], ability.extract(case["input"])) == []

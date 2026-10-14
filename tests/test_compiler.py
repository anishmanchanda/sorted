"""Full ability lifecycle, offline: LLM traces -> candidate -> tested -> shadow -> active -> degraded -> v2."""

from dataclasses import replace

from sqlalchemy import select

from brain import db
from brain.compiler import detector, registry
from brain.compiler.generator import compile_pending, split_cases
from brain.eval import load_labels, sample_id
from brain.orchestrator import Orchestrator
from brain.validate import Extraction

PARSER_V1 = r'''
import re

def extract(text):
    amt = re.search(r"Net Amount Payable \(Rs\.\)\s*([\d,]+\.\d{2})", text)
    due = re.search(r"Due Date\s*(\d{2})\.(\d{2})\.(\d{4})", text)
    if not (amt and due):
        raise ValueError("layout changed")
    d, m, y = due.groups()
    return {"type": "bill_due", "provider": "BSES Rajdhani", "amount": float(amt.group(1).replace(",", "")),
            "currency": "INR", "due_date": f"{y}-{m}-{d}"}
'''
PARSER_V2 = PARSER_V1.replace(r"Net Amount Payable \(Rs\.\)", r"(?:Net Amount Payable|Total Payable) \(Rs\.\)")


def _rows(model):
    with db.Session() as s:
        return s.scalars(select(model).order_by(model.id)).all()


def test_ability_lifecycle(fixtures, make_llm, monkeypatch):
    monkeypatch.setenv("BRAIN_SHADOW_RUNS", "1")
    labels = load_labels()
    bses = [m for m in fixtures if m.raw_path.endswith("_bses.eml")]
    by_text = {m.redacted_text(): labels[sample_id(m.raw_path)] for m in bses}
    broken = replace(bses[5], body=bses[5].body.replace("Net Amount Payable", "Total Payable"))
    by_text[broken.redacted_text()] = labels[sample_id(bses[5].raw_path)]
    code = {"v": PARSER_V1}

    def answer(user, schema):
        if schema.__name__ == "CodeGen":
            return {"code": code["v"]}
        lab = next(lab for text, lab in by_text.items() if text in user)
        return {k: v for k, v in lab.items() if k in Extraction.model_fields}

    llm = make_llm(answer)
    orch = Orchestrator(llm=llm)
    for m in bses[:3]:  # Apr-Jun through the LLM
        assert orch.ingest(m)["handler"] == "llm"

    with db.Session() as s:
        results = compile_pending(s, llm)
        s.commit()
    assert [(r["ability"], r["status"], r["visible"], r["held_out"]) for r in results] == \
        [("bsesdelhi_com_bill_due", "tested", 2, 1)]
    assert _rows(db.Ability)[0].trigger_json["subject_keywords"] == ["bill", "bses", "electricity", "rajdhani"]
    assert sum(t.held_out for t in _rows(db.AbilityTest)) == 1

    with db.Session() as s:
        registry.approve(s, "bsesdelhi_com_bill_due")
        s.commit()
    out = orch.ingest(bses[3])  # Jul: shadow run, LLM result used
    assert out["handler"] == "llm" and "-> active" in out["event"]

    calls = len(llm.calls)
    out = orch.ingest(bses[4])  # Aug: local code, no LLM call
    assert out["handler"] == "ability:bsesdelhi_com_bill_due@v1" and len(llm.calls) == calls
    assert out["extraction"].amount == labels[sample_id(bses[4].raw_path)]["amount"]

    out = orch.ingest(broken)  # layout change: validation fails -> degraded -> LLM fallback
    assert out["handler"] == "llm" and "degraded" in out["event"] and out["outcome"] == "open"
    assert _rows(db.Ability)[0].status == "degraded"

    code["v"] = PARSER_V2
    with db.Session() as s:
        results = compile_pending(s, llm)
        s.commit()
    assert [(r["ability"], r["version"], r["status"]) for r in results] == [("bsesdelhi_com_bill_due", 2, "tested")]
    v1, v2 = _rows(db.Ability)
    assert (v1.version, v1.status, v2.status) == (1, "degraded", "tested")  # v1 kept in the table
    v2_cases = [t for t in _rows(db.AbilityTest) if t.ability_id == v2.id]
    assert any("Total Payable" in t.input and not t.held_out for t in v2_cases)  # the new layout is always visible
    assert len([t for t in _rows(db.Trace) if t.task_kind == "compile"]) == 2


def test_static_check_failure_feeds_one_retry(fixtures, label_llm, make_llm):
    orch = Orchestrator(llm=label_llm)
    for m in [m for m in fixtures if m.raw_path.endswith("_lic.eml")][:3]:
        orch.ingest(m)
    attempts = []

    def answer(user, schema):
        attempts.append(user)
        return {"code": "import os\ndef extract(text):\n    return {}"}

    with db.Session() as s:
        [res] = compile_pending(s, make_llm(answer))
        s.commit()
    assert res["status"] == "candidate" and "import of 'os' not allowed" in res["error"]
    assert len(attempts) == 2 and "Static check rejected" in attempts[1]
    with db.Session() as s:  # no new traces -> not retried
        assert detector.scan(s) == []


def test_held_out_split_is_30_percent_and_deterministic():
    ab = db.Ability(name="x", version=1)
    items = [(db.Trace(output_json={"type": "bill_due"}), db.SourceRecord(id=i, text=str(i))) for i in range(10)]
    a, b = split_cases(ab, items), split_cases(ab, items)
    assert sum(c["held_out"] for c in a) == 3 and a == b

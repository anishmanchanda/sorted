# ruff: noqa: E501 (a document generator: long literal lines are the content)
"""Write docs/rebuild/03_PROMPTS.md from the live prompt constants, so the copy is exact."""
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from brain import agents, planner, query, sim, skills  # noqa: E402
from brain.compiler import generator  # noqa: E402

out = ["# Prompts, verbatim", "",
       "Generated from the code by reading the prompt constants, so every character matches the build these docs",
       "describe. All LLM calls go through `LLM.json(route, system, user, schema, run_id, cache_key)`: the provider",
       "is asked for `response_format={\"type\": \"json_object\"}`, the reply is validated against the Pydantic",
       "`schema`, and on a validation error the model gets ONE repair turn (see the end of this file).",
       "**The user turn is always redacted inside `LLM.json` before it is sent.**", ""]

def block(title, where, route, schema, user_turn, text):
    out.extend([f"## {title}", "", f"- **Constant:** `{where}`", f"- **Route:** `{route}`",
                f"- **Output schema:** {schema}", f"- **User turn:** {user_turn}", "", "```text", text.rstrip(), "```", ""])

block("1. Extraction (Inbox and Document agents)", "brain/agents.py: EXTRACT_SYSTEM", "small",
      "`Extraction` (02_CONTRACTS.md §2)",
      "`EMAIL:\\n<redacted text>` (Inbox agent, emails) or `DOCUMENT:\\n<redacted text>` (Document agent, SMS and PDFs: its `kind` argument upper-cased). When categories for "
      "`other` exist, it is prefixed with `KNOWN CATEGORIES: a, b\\n\\n`. Committed samples pass "
      "`cache_key=\"extract:<sample id>\"`.", agents.EXTRACT_SYSTEM)
block("2. Chat answers from state", "brain/agents.py: CHAT_SYSTEM", "small",
      "`Answer{answer: str, obligation_ids: list[int]}`",
      "`STATE:\\n<json context pack>\\n\\nQUESTION:\\n<question>`. The context pack has `today`, obligations "
      "(not paid/declined, due within 60 days ahead and 7 days back), subscriptions, documents, medications.",
      agents.CHAT_SYSTEM)
block("3. Planner (reminders and medicine tracking)", "brain/planner.py: PLAN_SYSTEM (formatted with today=)",
      "small", "`PlanRequest{kind: medication|reminder|none, name, dose, times[], stock, person, text, when, cron}`",
      "the user's request text. Only called when the text matches "
      "`\\b(remind|track|tablet|medicine|pill|daily|every (day|morning|night|week|month))\\b`.",
      planner.PLAN_SYSTEM)
block("4. Compiler agent: message parsers", "brain/compiler/generator.py: COMPILER_SYSTEM", "strong",
      "`CodeGen{code: str, notes: str}`", "see §5 for the exact user turn", generator.COMPILER_SYSTEM)

out.extend(["## 5. Compiler agent: the user turn and the header added to its code", "",
            "User turn, built by `_prompt()` (visible cases only; held-out cases are never shown):", "", "```text",
            "ABILITY: <name>", "OUTPUT_FIELDS: ['type', 'provider', 'amount', 'currency', 'due_date']   # fields present in the visible examples, in Extraction field order",
            "<blank line, or the topic note below when 'topic' is a field>",
            "EXAMPLES (input -> expected output):", "--- example 1 ---", "INPUT:", "<redacted message text>",
            "EXPECTED:", "<json of the accepted extraction>", "--- example 2 ---", "...", "```", "",
            "When `topic` is an output field the blank line is replaced with:", "", "```text",
            "topic is a free summary: return a short phrase from the message (e.g. the subject); any non-empty text passes.",
            "```", "",
            "Retry turn (attempt 2 of 2), appended to the same user turn:", "", "```text",
            "<the user turn above>", "", "YOUR PREVIOUS CODE:", "<code>", "", "PROBLEMS:",
            "example 2: expected {...} got {...} (wrong: ['amount'])      # one line per failing visible case",
            "1 of 2 held-out cases (not shown to you) also failed; generalise.   # only if held-out cases failed",
            "Return the full corrected code.", "```", "",
            "or, when the static check rejected the code: `Static check rejected the code:\\n<one problem per line>`.", "",
            "The returned code is prefixed with this header (`HEADER`, formatted) before the static check and the "
            "sandbox; `trigger` excludes `n_traces`:", "", "```python", generator.HEADER.rstrip(), "```", ""])

block("6. Question planner (chat question -> typed query)", "brain/query.py: PLANNER_SYSTEM", "small",
      "`QuerySpec{intent, period, provider, start, end}` (02_CONTRACTS.md §8)", "the redacted question",
      query.PLANNER_SYSTEM)
block("7. Compiler agent: question recognisers", "brain/query.py: COMPILER_SYSTEM (with INTENT replaced by the intent)",
      "strong", "`CodeGen`",
      "`INTENT: <intent>\\n\\nEXAMPLES:\\nQUESTION: <q>\\n-> <json spec>` for positives, and "
      "`QUESTION: <q>\\n-> raise ValueError` for negatives (questions of other intents). Retry turn: "
      "`\\n\\nYOUR PREVIOUS CODE:\\n<code>\\n\\nPROBLEMS:\\n<lines>\\nReturn the full corrected code.` "
      "Cache key `qcompile:<name>:v<n>:n<traces>:attempt<k>`.", query.COMPILER_SYSTEM)
block("8. Skill planner (a new kind of message)", "brain/skills.py: PLAN_SYSTEM", "small",
      "`SkillPlan{title: str, action: remind_before_due|notify_on_arrival|track_only, why: str}`",
      "`CATEGORY: <category>\\nEXAMPLES:\\n- <provider>: <topic or subject>, date <due_date>, amount <amount>` "
      "(up to 8 lines). If the LLM is unavailable: title = category in words + \"s\", action = track_only.",
      skills.PLAN_SYSTEM)
block("9. Synthetic data generator (simulation only)", "brain/sim.py: GEN_SYSTEM", "small",
      "`GenBatch{label: str, messages: [GenMessage{kind: email|sms, sender, subject, body, at}]}`",
      "`TIMELINE: <first day> to <end day>; current simulated time <YYYY-MM-DDTHH:MM>\\n\\nREQUEST: <user text>`. "
      "At most 12 messages are kept; subjects and bodies are passed through an ASCII translation table "
      "(non-breaking hyphens/spaces, smart quotes -> ASCII).", sim.GEN_SYSTEM)

out.extend(["## 10. The repair turn (every call)", "",
            "If the first reply fails Pydantic validation, `LLM.json` appends the assistant's reply and this user "
            "turn, then validates the second reply; a second failure raises:", "", "```text",
            "That JSON failed validation:", "<pydantic ValidationError text>", "Return corrected JSON only.", "```", ""])
(root / "docs" / "rebuild" / "03_PROMPTS.md").write_text("\n".join(out))
print("ok", len(out))

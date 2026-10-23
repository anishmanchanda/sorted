# Rebuild kit: build Sorted from scratch

These files, together with the two documents we submitted to HackIIITD, are meant to be enough for a capable
coding model (or a person) to rebuild **Sorted** from an empty folder and end up with this project:
- the same architecture and contracts;
- the same prompts and the same synthetic dataset;
- the same demo and the same 60 tests.

The proposal says **what** and **why**; this kit says **how**, exactly.

**Inputs to hand over:**
1. `Personal_Admin_Brain_HackIIITD.pdf`: the 9-slide deck (the pitch).
2. [`../design.pdf`](../design.pdf): the 27-page design draft (the full idea, much of it not built yet).
3. This folder, read in the order below.

| # | File | What it pins down |
|---|---|---|
| 0 | [`00_BRIEF.md`](00_BRIEF.md) | Scope, hard rules, and every place the build deliberately differs from the PDFs |
| 1 | [`01_ARCHITECTURE.md`](01_ARCHITECTURE.md) | Repo layout, module responsibilities, the message pipeline, the processes |
| 2 | [`02_CONTRACTS.md`](02_CONTRACTS.md) | Data model, schemas, validation, state semantics, every interface (CLI, Telegram, web API, MCP, webhook) |
| 3 | [`03_PROMPTS.md`](03_PROMPTS.md) | Every LLM prompt, verbatim (generated from the code), with schemas and user-turn formats |
| 4 | [`04_COMPILER.md`](04_COMPILER.md) | Detector, compiler loop, static check, sandbox, lifecycle, repair; compiled questions; new skills; the classifier |
| 5 | [`05_DATASET.md`](05_DATASET.md) | The synthetic household inbox, message by message, plus labels and date shifting |
| 6 | [`06_SIMULATION_AND_UI.md`](06_SIMULATION_AND_UI.md) | `make demo`, the interactive engine, autopilot, dashboard, Telegram front end |
| 7 | [`07_CONSTANTS.md`](07_CONSTANTS.md) | Every threshold, default and env var |
| 8 | [`08_PITFALLS.md`](08_PITFALLS.md) | Lessons learned the hard way; read before writing code |
| 9 | [`09_MILESTONES_AND_TESTS.md`](09_MILESTONES_AND_TESTS.md) | Build order, "done when" for each step, and the 60 tests to write |

Also useful once the build exists: [`../FEATURES.md`](../FEATURES.md) (the finished feature list) and
[`../PROPOSAL_VS_BUILT.md`](../PROPOSAL_VS_BUILT.md) (which parts of the PDFs are in scope).

## Suggested instruction to the model

> Build the project described by the two PDFs, following `docs/rebuild/` exactly. Read every file in the kit
> before writing code. The PDFs describe the full vision; the kit defines the version to build, and wins wherever
> they differ (`00_BRIEF.md` lists the differences). Work milestone by milestone (`09_MILESTONES_AND_TESTS.md`):
> write that milestone's tests, make them pass, run the linter, then move on. Tests must stay offline: mock every
> LLM, TinyFish and HTTP call. Use the prompts in `03_PROMPTS.md` character for character. Never invent numbers
> for the README; copy them from the generated `reports/`.

## How close will the rebuild be?

- **Identical:**
  - the code structure, contracts, prompts and dataset;
  - the behaviour of everything that runs without an LLM (scheduler, rules, reply handlers, redaction, filters,
    sandbox, static check, state, simulation clock, dashboard);
  - the offline tests.
- **Close, not identical:** anything that depends on live LLM output. The compiled parsers, per-month privacy
  percentages, token counts and costs change on every live recording. The originals were 0 / 0 / 7 / 0 / 62 / 47%
  local code per Sim month, with 11 parser versions; a rebuild should land in the same shape (nothing local
  before the end of Sim month 3, a big jump in Sim month 5, a dip in Sim month 6 from the HDFC layout change).
- **Not included:** API keys, the Telegram bot token, and the recorded LLM cache. The first `make demo` with keys
  re-records the cache: about 80 calls, roughly $0.10–0.15.

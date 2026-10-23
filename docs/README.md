# Sorted: project documents

**Sorted** is what we built from **Personal Admin Brain**, Team Not Found's HackIIITD 2026 (IIIT Delhi) Round 1
submission. The idea is unchanged: a household-admin assistant that uses **AI as a compiler, not an interpreter**.
The AI learns each new kind of task, a compiler agent turns what it learned into tested Python, and that code then
does the work with no AI call, so the assistant gets cheaper and more private every month.

| Document | What it is |
|---|---|
| [`FEATURES.md`](FEATURES.md) | Every feature that is built and working, where it lives in the code, and how to see it |
| [`PROPOSAL_VS_BUILT.md`](PROPOSAL_VS_BUILT.md) | The submitted deck and design doc, item by item: built, built differently, planned, or beyond the proposal; targets next to measured numbers |
| [`rebuild/`](rebuild/README.md) | **Rebuild kit:** everything needed to rebuild Sorted from scratch from the two PDFs (contracts, verbatim prompts, dataset spec, constants, pitfalls, milestones and tests) |
| [`design.pdf`](design.pdf) | The original 27-page design draft (12-week plan) |
| [`../DEMO.md`](../DEMO.md) | How to run and present the demo (`make demo`, `make sim`, Telegram `/run`) |
| [`../README.md`](../README.md) | The judge-facing overview with results and architecture |

The submitted deck (`Personal_Admin_Brain_HackIIITD.pdf`, 9 slides) is not in the repo; `PROPOSAL_VS_BUILT.md`
quotes the parts it maps.

## In one minute

- **Built:** all six MVP components the deck promised for the final (Telegram bot, email ingestion, TinyFish
  portal check, a compiled ability, AI-free reminders, the Brain MCP server) and the live metrics.
- **Also built:**
  - the full graduation pipeline: LLM → candidate → compiled + tested on held-out cases → approved → shadow →
    active → degraded → v2;
  - a local ML classifier, YAML rules, a medicine tracker and redaction.
- **Beyond the proposal:**
  - compiled chat questions;
  - Sorted noticing new kinds of messages and proposing skills for them;
  - meeting requests booked with your permission;
  - date-range digests;
  - an interactive six-month simulation with a web dashboard and a one-command Telegram autopilot.
- **Measured** on six simulated months of synthetic mail (`reports/`): 0% of messages handled by local code in Sim
  months 1–2, **62%** in Sim month 5; 100% extraction accuracy on type, provider and due date.
- **Not yet built:** Android SMS app, iPhone Shortcut, Gmail/Calendar MCP clients, Docker sandbox, encryption at
  rest, OCR, WhatsApp/Discord, the Auditor agent, TinyFish portal-script replay.

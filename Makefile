.PHONY: setup dataset demo demo-live sim test eval train lint bot mcp mcp-http

setup:
	uv sync
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example; add your API keys")
	uv run brain init

dataset:  ## regenerate the committed synthetic dataset (data/samples) so it ends today; then re-run make demo
	uv run python -m brain.samples

demo:  ## synthetic 6-month simulation in data/demo.db (never the live DB); replays data/llm_cache
	uv run python -m brain.demo

sim:  ## interactive simulation: web dashboard on http://127.0.0.1:8000 + your Telegram bot (stop make bot first)
	uv run python -m brain.web

demo-live:  ## same, but every LLM call goes to the providers
	uv run python -m brain.demo --live

test:
	uv run pytest -q

lint:
	uv run ruff check brain tests

eval:  ## re-score the last `make demo` run
	@test -f data/demo.db || (echo "run make demo first" && exit 1)
	BRAIN_DB_URL=sqlite:///data/demo.db BRAIN_LABELS=data/demo/labels.jsonl BRAIN_SAMPLES_DIR=data/demo/samples uv run python -m brain.eval

train:  ## retrain the local classifier on labelled samples + LLM-labelled messages
	uv run python -m brain.ml.train

bot:  ## Telegram bot + scheduler (needs TELEGRAM_BOT_TOKEN)
	uv run python -m brain.telegram_bot

mcp:  ## Brain MCP server over stdio (for Claude Desktop / Cursor)
	uv run python -m brain.mcp_server

mcp-http:  ## Streamable HTTP on 127.0.0.1:8765/mcp, needs BRAIN_MCP_TOKEN
	uv run python -m brain.mcp_server --http

.PHONY: setup samples demo demo-live test eval train lint bot mcp mcp-http

setup:
	uv sync
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example; add your API keys")
	uv run brain init

samples:
	uv run python scripts/gen_samples.py

demo:  ## resets data/brain.db; replays recorded LLM calls from data/llm_cache (live call on a cache miss)
	uv run python -m brain.demo

demo-live:  ## same, but every LLM call goes to the providers
	uv run python -m brain.demo --live

test:
	uv run pytest -q

lint:
	uv run ruff check brain tests scripts

eval:
	uv run python -m brain.eval

train:  ## retrain the local classifier on labelled samples + LLM-labelled messages
	uv run python -m brain.ml.train

bot:  ## Telegram bot + scheduler (needs TELEGRAM_BOT_TOKEN)
	uv run python -m brain.telegram_bot

mcp:  ## Brain MCP server over stdio (for Claude Desktop / Cursor)
	uv run python -m brain.mcp_server

mcp-http:  ## Streamable HTTP on 127.0.0.1:8765/mcp, needs BRAIN_MCP_TOKEN
	uv run python -m brain.mcp_server --http

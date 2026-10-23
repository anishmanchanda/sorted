"""`make sim`: the interactive simulation, as a web dashboard (http://127.0.0.1:8000) and, if
TELEGRAM_BOT_TOKEN is set, through your Telegram bot. Stop `make bot` first: one bot token, one poller."""

from brain import sim_env

sim_env.use()  # before any other brain import: everything below runs on data/demo.db

import logging  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

import uvicorn  # noqa: E402

from brain import config  # noqa: E402
from brain.sim import Engine  # noqa: E402
from brain.web.server import create_app  # noqa: E402

engine = Engine()


@asynccontextmanager
async def lifespan(app):
    bot = None
    token = config.env("TELEGRAM_BOT_TOKEN")
    if token and config.env("BRAIN_SIM_TELEGRAM", "1") != "0":
        from brain.web import telegram_sim

        bot = await telegram_sim.start(engine, token)
        print("Telegram: the simulation is live in your bot. Send /start, then /next.")
    yield
    if bot:
        await telegram_sim.stop(bot)


if __name__ == "__main__":
    logging.getLogger("httpx").setLevel(logging.WARNING)  # request URLs contain the bot token
    port = int(config.env("BRAIN_SIM_PORT", "8000"))
    print(f"Sorted simulation dashboard: http://127.0.0.1:{port}")
    uvicorn.run(create_app(engine, lifespan), host="127.0.0.1", port=port, log_level="warning")

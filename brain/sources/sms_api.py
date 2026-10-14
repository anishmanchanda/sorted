"""POST /ingest/sms: webhook for the (planned) Android companion app and iPhone Shortcuts automation.

Auth: per-user bearer tokens from BRAIN_INGEST_TOKENS="alice:<token>,bob:<token>".
Run: `brain serve-sms` (uvicorn on 127.0.0.1:8787).
"""

import secrets
from datetime import datetime
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from brain import config
from brain.messages import Message, to_ist_naive
from brain.orchestrator import Orchestrator

app = FastAPI(title="Sorted ingest")


class SMSIn(BaseModel):
    sender: str
    body: str
    received_at: datetime | None = None


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()


def user_for(authorization: str = Header(default="")) -> str:
    token = authorization.removeprefix("Bearer ").strip()
    for pair in filter(None, config.env("BRAIN_INGEST_TOKENS").split(",")):
        user, _, expected = pair.strip().partition(":")
        if token and expected and secrets.compare_digest(token, expected):
            return user
    raise HTTPException(status_code=401, detail="invalid token")


@app.post("/ingest/sms")
def ingest_sms(item: SMSIn, user: str = Depends(user_for), orch: Orchestrator = Depends(get_orchestrator)):
    received = to_ist_naive(item.received_at or datetime.now().astimezone())
    out = orch.ingest(Message("sms", item.sender, "", item.body, received, f"sms:webhook:{user}"))
    return {k: v for k, v in out.items() if k != "extraction"}

"""JSON API + single-page dashboard over the simulation engine. Endpoints are sync: FastAPI runs them in a
thread pool, and the engine serialises work with its own lock."""

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from brain import db, meetings

INDEX = Path(__file__).with_name("index.html")


class Step(BaseModel):
    to: str


class Settings(BaseModel):
    auto_approve: bool


class Chat(BaseModel):
    text: str


class Act(BaseModel):
    action: str


class Run(BaseModel):
    speed: str = "normal"  # fast / normal / slow
    generate: bool = True


class Speed(BaseModel):
    speed: str


class Generate(BaseModel):
    request: str


class NewMessage(BaseModel):
    kind: str = "email"
    sender: str
    subject: str = ""
    body: str
    at: str | None = None  # ISO datetime on the simulated clock; default: one minute from now


def create_app(engine, lifespan=None) -> FastAPI:
    app = FastAPI(title="Sorted simulation", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX.read_text()

    @app.get("/api/state")
    def state():
        return {"status": engine.status(), "stats": engine.stats()}

    @app.get("/api/feed")
    def feed(after: int = 0):
        return [e for e in engine.feed if e["id"] > after]

    @app.get("/api/abilities")
    def abilities():
        return engine.abilities()

    @app.get("/api/messages")
    def messages():
        return engine.dataset()

    @app.get("/api/messages/{sid}")
    def message(sid: str):
        try:
            return engine.message(sid)
        except StopIteration:
            raise HTTPException(404, f"no message {sid}") from None

    @app.post("/api/messages")
    def add_message(m: NewMessage):
        at = datetime.fromisoformat(m.at) if m.at else None
        return {"id": engine.add_message(m.kind, m.sender, m.subject, m.body, at)}

    @app.get("/api/months")
    def months():
        return engine.months()

    @app.post("/api/run")
    def run(r: Run):
        return {"started": engine.start_autopilot(r.speed, r.generate)}

    @app.post("/api/speed")
    def speed(sp: Speed):
        return {"speed": engine.set_speed(sp.speed)}

    @app.get("/api/learned")
    def learned():
        return engine.learned()

    @app.post("/api/stop")
    def stop():
        engine.stop_autopilot()
        return {"stopping": True}

    @app.post("/api/generate")
    def generate(g: Generate):
        if not g.request.strip():
            raise HTTPException(400, "describe the messages to generate")
        return engine.generate(g.request.strip())

    @app.delete("/api/messages/added")
    def clear_added():
        return {"removed": engine.clear_added()}

    @app.get("/api/outbox")
    def outbox():
        return engine.outbox()

    @app.post("/api/step")
    def step(s: Step):
        if s.to not in ("next", "day", "week", "month", "end"):
            raise HTTPException(400, "to must be next, day, week, month or end")
        if engine.autopilot_running():  # stepping by hand pauses the autopilot
            engine.stop_autopilot(wait=True)
        return {"events": engine.step(s.to)}

    @app.post("/api/settings")
    def settings(s: Settings):
        engine.set_auto_approve(s.auto_approve)
        return {"auto_approve": s.auto_approve}

    @app.post("/api/reset")
    def reset():
        engine.reset()
        return {"ok": True}

    @app.post("/api/chat")
    def chat(c: Chat):
        return engine.ask(c.text)

    @app.post("/api/action")
    def action(a: Act):
        out = engine.act(a.action)
        if out.get("ics"):
            out["ics_url"] = f"/api/ics/{a.action.split(':')[1]}"
        return {k: v for k, v in out.items() if k != "ics"}

    @app.get("/api/ics/{source_id}")
    def ics(source_id: int):
        with db.Session() as s:
            ob = meetings.obligation_for(s, source_id)
            if ob is None:
                raise HTTPException(404)
            body = meetings.ics(meetings.title_of(ob), meetings.start_of(ob), f"meet{ob.id}",
                                location=meetings.meet_link(ob.id))
        return Response(body, media_type="text/calendar",
                        headers={"Content-Disposition": f'attachment; filename="meeting-{source_id}.ics"'})

    return app

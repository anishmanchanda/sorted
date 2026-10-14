"""SQLite state store (SQLAlchemy 2.0). Every fact row points at the source_records row it came from.

Scheduler jobs live in APScheduler's own `apscheduler_jobs` table (SQLAlchemyJobStore, same DB file).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from brain import config


class Base(DeclarativeBase):
    pass


class SourceRecord(Base):
    __tablename__ = "source_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # email / sms / pdf / chat / web
    sender: Mapped[str] = mapped_column(String(255), default="")
    subject: Mapped[str] = mapped_column(String(500), default="")
    body_hash: Mapped[str] = mapped_column(String(64), unique=True)
    received_at: Mapped[datetime] = mapped_column(DateTime)
    raw_path: Mapped[str] = mapped_column(String(500), default="")
    # Redacted text: the only form agents, abilities and the compiler ever see. Raw stays at raw_path.
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="new")  # new / done / queued


class Obligation(Base):
    __tablename__ = "obligations"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(40))  # bill / premium / renewal / subscription / meeting
    provider: Mapped[str] = mapped_column(String(120))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    due_date: Mapped[date | None] = mapped_column(Date)
    repeat_rule: Mapped[str] = mapped_column(String(60), default="")  # e.g. "monthly"
    status: Mapped[str] = mapped_column(String(20), default="open")  # open / paid / flagged
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    note: Mapped[str] = mapped_column(Text, default="")  # validation / conflict flags
    source_id: Mapped[int] = mapped_column(ForeignKey("source_records.id"))


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    service: Mapped[str] = mapped_column(String(120), unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    effective_date: Mapped[date | None] = mapped_column(Date)
    source_id: Mapped[int] = mapped_column(ForeignKey("source_records.id"))


class Medication(Base):
    __tablename__ = "medications"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str] = mapped_column(String(60))
    times: Mapped[str] = mapped_column(String(60))  # comma separated HH:MM
    stock: Mapped[int] = mapped_column(Integer)
    person: Mapped[str] = mapped_column(String(60), default="me")
    source_id: Mapped[int] = mapped_column(ForeignKey("source_records.id"))


class DoseLog(Base):
    __tablename__ = "dose_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    medication_id: Mapped[int] = mapped_column(ForeignKey("medications.id"))
    taken_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(60))  # puc / insurance_policy / passport ...
    expiry: Mapped[date | None] = mapped_column(Date)
    source_id: Mapped[int] = mapped_column(ForeignKey("source_records.id"))


class Trace(Base):
    __tablename__ = "traces"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40))
    task_kind: Mapped[str] = mapped_column(String(40))  # classify / extract / chat / compile / portal
    input_ref: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"))
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    handler: Mapped[str] = mapped_column(String(80))  # "llm" or "ability:<name>@v<n>"
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)  # USD
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Ability(Base):
    __tablename__ = "abilities"
    __table_args__ = (UniqueConstraint("name", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20), default="parser")  # parser / classifier / rule
    trigger_json: Mapped[dict] = mapped_column(JSON, default=dict)
    code: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    # candidate / generated / tested / shadow / active / degraded / retired
    status: Mapped[str] = mapped_column(String(20), default="candidate")
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    runs: Mapped[int] = mapped_column(Integer, default=0)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    shadow_matches: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AbilityTest(Base):
    __tablename__ = "ability_tests"
    id: Mapped[int] = mapped_column(primary_key=True)
    ability_id: Mapped[int] = mapped_column(ForeignKey("abilities.id"))
    input: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[dict] = mapped_column(JSON)
    held_out: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actor: Mapped[str] = mapped_column(String(60))  # agent / ability / user / mcp
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


# in-memory DB (tests): one shared connection so every thread sees the same database
engine = (create_engine(config.DB_URL, poolclass=StaticPool, connect_args={"check_same_thread": False})
          if config.DB_URL == "sqlite://" else create_engine(config.DB_URL))
Session = sessionmaker(engine, expire_on_commit=False)


def init_db() -> None:
    if config.DB_URL.startswith("sqlite:///"):
        config.ROOT.joinpath("data").mkdir(exist_ok=True)
    Base.metadata.create_all(engine)


def audit(session, actor: str, action: str, **detail) -> None:
    session.add(AuditLog(actor=actor, action=action, detail=detail))

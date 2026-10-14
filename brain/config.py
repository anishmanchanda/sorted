"""All settings come from env vars (optionally loaded from .env). No hardcoded model IDs."""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


DB_URL = env("BRAIN_DB_URL", f"sqlite:///{ROOT / 'data' / 'brain.db'}")
SAMPLES_DIR = ROOT / "data" / "samples"
LABELS_PATH = ROOT / "data" / "eval" / "labels.jsonl"
REPORTS_DIR = ROOT / "reports"

COMPILE_AFTER = int(env("BRAIN_COMPILE_AFTER", "3"))
SHADOW_RUNS = int(env("BRAIN_SHADOW_RUNS", "2"))
CLASSIFIER_THRESHOLD = float(env("BRAIN_CLASSIFIER_THRESHOLD", "0.7"))
QUIET_HOURS = env("BRAIN_QUIET_HOURS", "22-07")


def today() -> date:
    """BRAIN_TODAY pins 'now' for the simulated-month demo; otherwise the real date."""
    return date.fromisoformat(v) if (v := env("BRAIN_TODAY")) else date.today()

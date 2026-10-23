"""Point a process at the simulation's own files. Call before importing any other brain module, because config,
db.engine and the classifier path read the environment at import time."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "data" / "demo"


def use() -> None:
    os.environ.update({
        "BRAIN_DB_URL": f"sqlite:///{ROOT / 'data' / 'demo.db'}",  # never the live DB
        "BRAIN_MODEL_DIR": str(DEMO / "models"),
        "BRAIN_ABILITIES_DIR": str(DEMO / "abilities"),
        "BRAIN_SHADOW_RUNS": os.environ.get("BRAIN_SIM_SHADOW_RUNS", "1"),
        "BRAIN_USER_NAME": "Rohan",  # the synthetic persona signs meeting replies
    })

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "instance" / "real_estate.db"


def database_path() -> Path:
    configured = os.environ.get("REAL_PRICE_DB")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH


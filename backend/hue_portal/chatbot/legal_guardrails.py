"""
Guardrails RAIL schema and helpers for structured legal answers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from guardrails import Guard

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
RAIL_PATH = SCHEMA_DIR / "legal_answer.rail"


@lru_cache(maxsize=1)
def get_legal_guard() -> Guard:
    """Return cached Guard instance for legal answers."""

    return Guard.from_rail(rail_file=str(RAIL_PATH))


def ensure_schema_files() -> Optional[Dict[str, str]]:
    """
    Return metadata for the legal RAIL schema to help packaging.

    Called during setup to make sure the schema file is discovered by tools
    such as setup scripts or bundlers.
    """

    if RAIL_PATH.exists():
        return {"legal_rail": str(RAIL_PATH)}
    return None


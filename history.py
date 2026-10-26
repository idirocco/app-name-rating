"""Small JSON-backed history store for the MVP.

This deliberately avoids a database. Storage is best-effort on platforms with
ephemeral disks, but remains useful locally and can always be exported.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_PATH = Path(__file__).parent / ".data" / "evaluated_names.json"


def load_history(path: Path = HISTORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def append_evaluations(evaluations: list[dict[str, Any]], path: Path = HISTORY_PATH) -> list[dict[str, Any]]:
    """Persist evaluations atomically and return the newest-first history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    additions = []
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for evaluation in evaluations:
        additions.append({**evaluation, "evaluated_at": timestamp})
    history = additions + load_history(path)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary_path, path)
    return history


def history_by_normalized_name(history: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return the newest saved result for each name, case-insensitively."""
    matches: dict[str, dict[str, Any]] = {}
    for evaluation in history:
        name = evaluation.get("name")
        if isinstance(name, str) and name.strip():
            matches.setdefault(" ".join(name.split()).casefold(), evaluation)
    return matches

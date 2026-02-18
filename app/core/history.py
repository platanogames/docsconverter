from __future__ import annotations

import json
from pathlib import Path


def read_history(history_path: Path, limit: int = 100) -> list[dict]:
    if not history_path.exists():
        return []
    entries: list[dict] = []
    with history_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    # Most recent first
    entries.reverse()
    return entries[:limit]


def append_history(history_path: Path, entry: dict) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

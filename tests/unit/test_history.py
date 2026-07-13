from pathlib import Path

from app.core.history import append_history, read_history


def test_append_and_read_history(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    entry = {"format": "html", "return_code": 0, "output_path": "out.html"}
    append_history(history_path, entry)
    entries = read_history(history_path)
    assert len(entries) == 1
    assert entries[0]["format"] == "html"
    assert entries[0]["return_code"] == 0


def test_read_history_returns_most_recent_first(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    append_history(history_path, {"format": "html", "return_code": 0})
    append_history(history_path, {"format": "pdf", "return_code": 0})
    entries = read_history(history_path)
    assert entries[0]["format"] == "pdf"
    assert entries[1]["format"] == "html"


def test_read_history_missing_file(tmp_path: Path) -> None:
    entries = read_history(tmp_path / "nonexistent.jsonl")
    assert entries == []


def test_read_history_respects_limit(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    for i in range(10):
        append_history(history_path, {"format": "html", "index": i})
    entries = read_history(history_path, limit=3)
    assert len(entries) == 3

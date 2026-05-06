"""
Store word lookups in a local JSON file.
Writes are buffered: flush every 5 entries or on process exit.
"""

import json
import sys
from pathlib import Path

_buffer: list[dict] = []


def _get_json_path() -> Path:
    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / "english_words.json"


def add_word(query: str, results: str) -> None:
    """Buffer an English word lookup.  Flushes automatically every 5 entries.

    If the same query already exists in the buffer, increment its lookup_count
    instead of adding a duplicate.
    """
    global _buffer
    for entry in _buffer:
        if entry["query"] == query:
            entry["lookup_count"] += 1
            print(
                f"[word_store] '{query}' lookup_count → {entry['lookup_count']} (buffer size: {len(_buffer)})"
            )
            return
    _buffer.append({"query": query, "results": results, "lookup_count": 1})
    print(f"[word_store] added '{query}' (buffer size: {len(_buffer)})")
    if len(_buffer) >= 5:
        _flush()


def flush() -> None:
    """Write all buffered entries to disk immediately."""
    _flush()


def _flush() -> None:
    global _buffer
    if not _buffer:
        return

    path = _get_json_path()

    existing: list[dict] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []

    flush_count = len(_buffer)
    # Merge buffer into existing, deduplicating by query
    for buf_entry in _buffer:
        found = False
        for ex_entry in existing:
            if ex_entry["query"] == buf_entry["query"]:
                ex_entry["lookup_count"] = ex_entry.get("lookup_count", 1) + 1
                found = True
                break
        if not found:
            existing.append(buf_entry)

    path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[word_store] flushed {flush_count} entries to {path} (total: {len(existing)})"
    )
    _buffer.clear()

"""
db.py — In-memory mock SaaS database.

This is NOT a real database. It's a simple dict-based store that gets
seeded fresh before every scenario. That's exactly what HUD needs:
deterministic, isolated, reproducible state per eval run.
"""

from typing import Any
import copy

# ── The store ──────────────────────────────────────────────────────────────────
# Everything lives here. Reset by calling clear(), then seed with insert().

_store: dict[str, list[dict]] = {
    "tickets": [],
    "projects": [],
    "tasks": [],
    "users": [],
    "comments": [],
}

_next_id: dict[str, int] = {k: 1 for k in _store}


# ── Core operations ────────────────────────────────────────────────────────────

def clear() -> None:
    """Wipe all tables and reset IDs. Call this at the start of every scenario."""
    for key in _store:
        _store[key] = []
        _next_id[key] = 1


def insert(table: str, **fields) -> int:
    """Insert a row. Auto-assigns an integer id. Returns the new id."""
    if table not in _store:
        raise ValueError(f"Unknown table: {table}")
    row_id = _next_id[table]
    _next_id[table] += 1
    row = {"id": row_id, **fields}
    _store[table].append(copy.deepcopy(row))
    return row_id


def get(table: str, **filters) -> dict | None:
    """Return the first row matching all filters, or None."""
    for row in _store[table]:
        if all(row.get(k) == v for k, v in filters.items()):
            return copy.deepcopy(row)
    return None


def query(table: str, **filters) -> list[dict]:
    """Return all rows matching all filters (empty dict = return all)."""
    return [
        copy.deepcopy(row)
        for row in _store[table]
        if all(row.get(k) == v for k, v in filters.items())
    ]


def update(table: str, row_id: int, **fields) -> dict | None:
    """Update fields on a row by id. Returns updated row or None if not found."""
    for row in _store[table]:
        if row["id"] == row_id:
            row.update(fields)
            return copy.deepcopy(row)
    return None


def delete(table: str, row_id: int) -> bool:
    """Delete a row by id. Returns True if deleted, False if not found."""
    original_len = len(_store[table])
    _store[table] = [r for r in _store[table] if r["id"] != row_id]
    return len(_store[table]) < original_len


def count(table: str, **filters) -> int:
    """Count rows matching filters."""
    return len(query(table, **filters))


def all_rows(table: str) -> list[dict]:
    """Return all rows in a table."""
    return copy.deepcopy(_store[table])
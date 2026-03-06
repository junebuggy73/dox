"""SQLite-based cache for fetched documentation pages."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "dox"
DEFAULT_TTL = 86400  # 24 hours


def _db_path() -> Path:
    DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CACHE_DIR / "cache.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.execute(
        """CREATE TABLE IF NOT EXISTS pages (
            url_hash TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            html TEXT NOT NULL,
            fetched_at REAL NOT NULL
        )"""
    )
    return conn


def _hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def get(url: str, ttl: int = DEFAULT_TTL) -> str | None:
    conn = _connect()
    row = conn.execute(
        "SELECT html, fetched_at FROM pages WHERE url_hash = ?", (_hash(url),)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    html, fetched_at = row
    if time.time() - fetched_at > ttl:
        return None
    return html


def put(url: str, html: str) -> None:
    conn = _connect()
    conn.execute(
        "INSERT OR REPLACE INTO pages (url_hash, url, html, fetched_at) VALUES (?, ?, ?, ?)",
        (_hash(url), url, html, time.time()),
    )
    conn.commit()
    conn.close()


def clear() -> int:
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    conn.execute("DELETE FROM pages")
    conn.commit()
    conn.close()
    return count


def stats() -> dict:
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    size = _db_path().stat().st_size if _db_path().exists() else 0
    conn.close()
    return {"entries": count, "size_bytes": size}

"""
persistence.py
==============

Camada de persistência do AHDC. Toda telemetria é gravada aqui — nunca
mantida apenas em memória. O formato escolhido é SQLite (arquivo único,
zero dependência de servidor, portátil entre Windows/Linux/WSL), mas o
acesso é encapsulado nesta classe para permitir troca futura de backend
sem tocar no restante do sistema.

Nenhuma lógica de negócio mora aqui. Isto é só um repositório de fatos.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    snapshot_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    category TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    version TEXT,
    path TEXT,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    UNIQUE(name, kind, path)
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    format TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    size_bytes INTEGER,
    modified_at REAL,
    content_hash TEXT,
    kind_guess TEXT,
    last_scanned REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    tool TEXT,
    model TEXT,
    metric TEXT NOT NULL,
    value REAL,
    payload_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_models_path ON models(path);
"""


class Store:
    """Wrapper fino sobre SQLite. Thread-safe via lock próprio."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # ---------------------------------------------------------------- snapshots
    def save_snapshot(self, snapshot: dict[str, Any]) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO snapshots (timestamp, snapshot_json) VALUES (?, ?)",
                (time.time(), json.dumps(snapshot, default=str)),
            )
            self._conn.commit()
            return cur.lastrowid

    def latest_snapshot(self) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT timestamp, snapshot_json FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        ts, payload = row
        data = json.loads(payload)
        data["_snapshot_timestamp"] = ts
        return data

    # ------------------------------------------------------------------- events
    def add_event(self, category: str, event_type: str, message: str,
                  payload: Optional[dict[str, Any]] = None) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO events (timestamp, category, event_type, message, payload_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (time.time(), category, event_type, message,
                 json.dumps(payload, default=str) if payload else None),
            )
            self._conn.commit()
            return cur.lastrowid

    def get_events(self, since: Optional[float] = None, category: Optional[str] = None,
                   limit: int = 500) -> list[dict[str, Any]]:
        query = "SELECT timestamp, category, event_type, message, payload_json FROM events WHERE 1=1"
        params: list[Any] = []
        if since is not None:
            query += " AND timestamp >= ?"
            params.append(since)
        if category is not None:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        result = []
        for ts, cat, etype, msg, payload in rows:
            result.append({
                "timestamp": ts,
                "category": cat,
                "event_type": etype,
                "message": msg,
                "payload": json.loads(payload) if payload else None,
            })
        return result

    # --------------------------------------------------------------- inventory
    def upsert_inventory(self, name: str, kind: str, version: Optional[str],
                          path: Optional[str]) -> None:
        now = time.time()
        with self._lock:
            cur = self._conn.execute(
                "SELECT id FROM inventory WHERE name=? AND kind=? AND path IS ?",
                (name, kind, path),
            )
            row = cur.fetchone()
            if row:
                self._conn.execute(
                    "UPDATE inventory SET version=?, last_seen=? WHERE id=?",
                    (version, now, row[0]),
                )
            else:
                self._conn.execute(
                    "INSERT INTO inventory (name, kind, version, path, first_seen, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (name, kind, version, path, now, now),
                )
            self._conn.commit()

    def get_inventory(self, kind: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT name, kind, version, path, first_seen, last_seen FROM inventory"
        params: list[Any] = []
        if kind:
            query += " WHERE kind = ?"
            params.append(kind)
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [
            {"name": n, "kind": k, "version": v, "path": p,
             "first_seen": fs, "last_seen": ls}
            for n, k, v, p, fs, ls in rows
        ]

    def known_inventory_names(self, kind: str) -> set[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT name FROM inventory WHERE kind=?", (kind,)
            ).fetchall()
        return {r[0] for r in rows}

    # ------------------------------------------------------------------ models
    def upsert_model(self, name: str, fmt: str, path: str, size_bytes: Optional[int],
                      modified_at: Optional[float], content_hash: Optional[str],
                      kind_guess: Optional[str]) -> None:
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO models (name, format, path, size_bytes, modified_at,
                                     content_hash, kind_guess, last_scanned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    name=excluded.name, format=excluded.format,
                    size_bytes=excluded.size_bytes, modified_at=excluded.modified_at,
                    content_hash=excluded.content_hash, kind_guess=excluded.kind_guess,
                    last_scanned=excluded.last_scanned
                """,
                (name, fmt, path, size_bytes, modified_at, content_hash, kind_guess, now),
            )
            self._conn.commit()

    def get_models(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT name, format, path, size_bytes, modified_at, content_hash, "
                "kind_guess, last_scanned FROM models"
            ).fetchall()
        cols = ["name", "format", "path", "size_bytes", "modified_at",
                "content_hash", "kind_guess", "last_scanned"]
        return [dict(zip(cols, row)) for row in rows]

    def known_model_paths(self) -> set[str]:
        with self._lock:
            rows = self._conn.execute("SELECT path FROM models").fetchall()
        return {r[0] for r in rows}

    def remove_model(self, path: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM models WHERE path=?", (path,))
            self._conn.commit()

    # --------------------------------------------------------------- benchmark
    def add_benchmark_result(self, tool: Optional[str], model: Optional[str],
                              metric: str, value: Optional[float],
                              payload: Optional[dict[str, Any]] = None) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO benchmark_results (timestamp, tool, model, metric, value, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), tool, model, metric, value,
                 json.dumps(payload, default=str) if payload else None),
            )
            self._conn.commit()
            return cur.lastrowid

    def get_benchmark_results(self, tool: Optional[str] = None,
                               limit: int = 200) -> list[dict[str, Any]]:
        query = ("SELECT timestamp, tool, model, metric, value, payload_json "
                  "FROM benchmark_results WHERE 1=1")
        params: list[Any] = []
        if tool:
            query += " AND tool = ?"
            params.append(tool)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        result = []
        for ts, tool_, model, metric, value, payload in rows:
            result.append({
                "timestamp": ts, "tool": tool_, "model": model, "metric": metric,
                "value": value, "payload": json.loads(payload) if payload else None,
            })
        return result

    def close(self) -> None:
        with self._lock:
            self._conn.close()

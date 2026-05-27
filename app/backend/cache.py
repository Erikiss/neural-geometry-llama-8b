from __future__ import annotations

import json
import os
import sqlite3
import uuid
from io import BytesIO
from pathlib import Path
from time import time

import numpy as np

from models import ConceptSpec, PromptItem, QueryResult

CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path(__file__).parent / "cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = CACHE_DIR / "cache.db"

SIMILARITY_THRESHOLD = 0.97


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            id          TEXT PRIMARY KEY,
            query       TEXT NOT NULL,
            layer       INTEGER NOT NULL,
            embedding   BLOB NOT NULL,
            result_json TEXT NOT NULL,
            created_at  REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def _emb_to_blob(emb: list[float]) -> bytes:
    arr = np.array(emb, dtype=np.float32)
    buf = BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


def _blob_to_emb(blob: bytes) -> np.ndarray:
    return np.load(BytesIO(blob))


def find_cached(embedding: list[float], layer: int) -> QueryResult | None:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, embedding, result_json FROM cache WHERE layer = ?", (layer,)
    ).fetchall()
    conn.close()

    if not rows:
        return None

    q = np.array(embedding, dtype=np.float32)
    q = q / (np.linalg.norm(q) + 1e-9)

    cached_embs = np.stack([_blob_to_emb(r[1]) for r in rows])
    norms = np.linalg.norm(cached_embs, axis=1, keepdims=True) + 1e-9
    cached_norm = cached_embs / norms
    sims = cached_norm @ q

    best = int(np.argmax(sims))
    if sims[best] >= SIMILARITY_THRESHOLD:
        result = QueryResult.model_validate_json(rows[best][2])
        result.cache_hit = True
        return result
    return None


def save_to_cache(
    embedding: list[float],
    query: str,
    layer: int,
    result: QueryResult,
) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO cache (id, query, layer, embedding, result_json, created_at) VALUES (?,?,?,?,?,?)",
        (
            str(uuid.uuid4()),
            query,
            layer,
            sqlite3.Binary(_emb_to_blob(embedding)),
            result.model_dump_json(),
            time(),
        ),
    )
    conn.commit()
    conn.close()


def delete_cached(query_filter: str | None = None) -> int:
    conn = _get_conn()
    if query_filter:
        cur = conn.execute(
            "DELETE FROM cache WHERE LOWER(query) LIKE LOWER(?)",
            (f"%{query_filter}%",),
        )
    else:
        cur = conn.execute("DELETE FROM cache")
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted


def get_recent(limit: int = 10) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT query, layer, result_json, created_at FROM cache ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    out = []
    for query, layer, result_json, created_at in rows:
        r = json.loads(result_json)
        out.append({
            "query": query,
            "concept_name": r.get("concept_name", query),
            "layer": layer,
            "is_cyclic": r.get("is_cyclic", False),
            "n_values": len(r.get("values", [])),
            "created_at": created_at,
        })
    return out

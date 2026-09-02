"""
Total-ReClaw memory — SQLite + FTS5 + embedding recall for atomic findings.

Persists high-probability anomalies across county runs. Injected before each
county audit via memory_recall() → <vault-memories> context block.
"""

from __future__ import annotations

import json
import sqlite3
import struct
import time
import uuid
from pathlib import Path

from tools.public_data_loaders import REPO_ROOT

MEMORY_DB = REPO_ROOT / "data" / "memory" / "reclaw_memory.db"


def _connect() -> sqlite3.Connection:
    MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(MEMORY_DB))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            county TEXT,
            category TEXT,
            content TEXT NOT NULL,
            embedding BLOB,
            score REAL DEFAULT 1.0,
            trust TEXT DEFAULT 'verified',
            provenance TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS fts_memories USING fts5(content, county, category, provenance)"
    )
    conn.commit()
    return conn


def _embed(text: str) -> bytes | None:
    try:
        from rag.embeddings import EmbeddingManager

        mgr = EmbeddingManager()
        mgr.load_model()
        vec = mgr._model.encode([text], normalize_embeddings=True)[0]
        return struct.pack(f"{len(vec)}f", *vec.astype("float32"))
    except Exception:
        return None


def _cosine(a: bytes, b: bytes) -> float:
    import numpy as np

    va = np.array(struct.unpack(f"{len(a)//4}f", a))
    vb = np.array(struct.unpack(f"{len(b)//4}f", b))
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def memory_save(
    content: str,
    *,
    county: str = "",
    category: str = "atomic_finding",
    provenance: str = "",
    score: float = 1.0,
    trust: str = "verified",
) -> str:
    """Persist an atomic finding with optional embedding."""
    mem_id = f"mem-{uuid.uuid4().hex[:12]}"
    emb = _embed(content)
    now = int(time.time())
    conn = _connect()
    conn.execute(
        """
        INSERT INTO memories (id, county, category, content, embedding, score, trust, provenance, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (mem_id, county, category, content, emb, score, trust, provenance, now),
    )
    conn.execute(
        "INSERT INTO fts_memories (content, county, category, provenance) VALUES (?, ?, ?, ?)",
        (content, county, category, provenance),
    )
    conn.commit()
    conn.close()
    return mem_id


def memory_recall(
    query: str,
    *,
    county: str | None = None,
    limit: int = 8,
    min_score: float = 0.35,
) -> list[dict]:
    """Retrieve related memories — FTS first, embedding cosine rerank when available."""
    conn = _connect()
    rows: list[sqlite3.Row] = []

    q = query.replace('"', "").strip()
    if q:
        try:
            rows = conn.execute(
                """
                SELECT m.* FROM memories m
                WHERE m.id IN (
                    SELECT rowid FROM fts_memories WHERE fts_memories MATCH ?
                )
                AND (? = '' OR m.county = ? OR m.county = '')
                ORDER BY m.score DESC, m.created_at DESC
                LIMIT ?
                """,
                (q, county or "", county or "", limit * 3),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
    if not rows:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY score DESC, created_at DESC LIMIT ?",
            (limit * 3,),
        ).fetchall()

    query_emb = _embed(query)
    ranked: list[tuple[float, dict]] = []
    for r in rows:
        item = dict(r)
        sim = 0.5
        if query_emb and item.get("embedding"):
            sim = _cosine(query_emb, item["embedding"])
        if sim >= min_score or not query_emb:
            ranked.append((sim * float(item.get("score") or 1), item))

    ranked.sort(key=lambda x: -x[0])
    conn.close()
    return [x[1] for x in ranked[:limit]]


def format_vault_memories(memories: list[dict]) -> str:
    """Wrap recalled memories for agent prompt injection."""
    if not memories:
        return ""
    lines = ["<vault-memories>"]
    for m in memories:
        lines.append(
            f"- [{m.get('county') or 'statewide'}/{m.get('category')}] "
            f"{m.get('content', '')[:300]} (provenance: {m.get('provenance', 'n/a')})"
        )
    lines.append("</vault-memories>")
    return "\n".join(lines)


def save_atomic_finding(
    county: str,
    description: str,
    *,
    category: str,
    evidence: str,
    severity: str,
) -> str | None:
    """Save high-severity flags to memory for cross-county recall."""
    if severity not in ("critical", "high"):
        return None
    return memory_save(
        description,
        county=county,
        category=category,
        provenance=evidence[:500] if evidence else "",
        score=1.0 if severity == "critical" else 0.85,
    )


def mount_status() -> dict:
    """Health check for orchestration bootstrap."""
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    conn.close()
    return {
        "path": str(MEMORY_DB),
        "mounted": MEMORY_DB.exists(),
        "memory_count": n,
        "backend": "sqlite3+fts5+sentence-transformers",
    }
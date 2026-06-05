"""L03 · 向量库（Retriever 的存储底座）。

仓储模式（与平台其它 store 一致）：默认内存，有 DATABASE_URL 走 PG。向量以 JSON 文本存，
检索时取回在 Python 里算余弦（向量已 L2 归一化 → 点积即余弦）。自用规模（千级块）足够，
零运维、不依赖 pgvector 扩展；将来量大可平滑换 pgvector（接口不变）。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class VectorRecord(BaseModel):
    """一个向量化的文档块。"""

    doc_id: str
    chunk_id: str
    text: str
    vector: list[float]
    meta: dict[str, Any] = Field(default_factory=dict)


def _cosine(a: list[float], b: list[float]) -> float:
    """归一化向量的余弦 = 点积。"""
    return sum(x * y for x, y in zip(a, b, strict=False))


class VectorStore(ABC):
    @abstractmethod
    def add(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    def search(self, query_vec: list[float], top_n: int) -> list[tuple[VectorRecord, float]]: ...

    @abstractmethod
    def clear_doc(self, doc_id: str) -> None:
        """删除某文档的全部块（重建索引前先清，避免残留旧块）。"""

    @abstractmethod
    def count(self) -> int: ...


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._records: list[VectorRecord] = []

    def add(self, records: list[VectorRecord]) -> None:
        self._records.extend(records)

    def search(self, query_vec: list[float], top_n: int) -> list[tuple[VectorRecord, float]]:
        scored = [(r, _cosine(query_vec, r.vector)) for r in self._records]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_n]

    def clear_doc(self, doc_id: str) -> None:
        self._records = [r for r in self._records if r.doc_id != doc_id]

    def count(self) -> int:
        return len(self._records)


class PgVectorStore(VectorStore):
    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS rag_vectors ("
                "seq serial PRIMARY KEY, doc_id text, chunk_id text, text text, "
                "vector text, meta text)"
            )

    def add(self, records: list[VectorRecord]) -> None:
        with self._pool.connection() as conn:
            for r in records:
                conn.execute(
                    "INSERT INTO rag_vectors (doc_id, chunk_id, text, vector, meta) VALUES (%s,%s,%s,%s,%s)",
                    (r.doc_id, r.chunk_id, r.text, json.dumps(r.vector), json.dumps(r.meta, ensure_ascii=False)),
                )

    def search(self, query_vec: list[float], top_n: int) -> list[tuple[VectorRecord, float]]:
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT doc_id, chunk_id, text, vector, meta FROM rag_vectors").fetchall()
        scored: list[tuple[VectorRecord, float]] = []
        for row in rows:
            rec = VectorRecord(
                doc_id=row[0],
                chunk_id=row[1],
                text=row[2],
                vector=json.loads(row[3]),
                meta=json.loads(row[4]) if row[4] else {},
            )
            scored.append((rec, _cosine(query_vec, rec.vector)))
        scored.sort(key=lambda x: -x[1])
        return scored[:top_n]

    def clear_doc(self, doc_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM rag_vectors WHERE doc_id=%s", (doc_id,))

    def count(self) -> int:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT count(*) FROM rag_vectors").fetchone()
        return int(row[0]) if row else 0


def build_vector_store(database_url: str = "") -> VectorStore:
    if database_url:
        try:
            return PgVectorStore(database_url)
        except Exception:
            pass
    return InMemoryVectorStore()

"""L03 · 知识语料库（RAG 的文档本体）。

存放可检索的非结构化知识文档（案例/手册/规程等，分类见知识库蓝本
docs/specs/knowledge-base.md）。仓储模式：默认内存，有 DATABASE_URL 走 PG。
注意：结构化数据（CMDB）按 C-25 走工具直查，不入此库——这里只放非结构化文本。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

# 与知识库蓝本一致的分类（非结构化 10 类）
CATEGORIES = (
    "历史告警处理记录",
    "事件处理记录",
    "复盘总结",
    "故障报告",
    "应用手册",
    "硬件手册",
    "产品说明书",
    "命令库",
    "运维手册",
    "运维及监管制度",
)


class KnowledgeDoc(BaseModel):
    """一篇知识文档。"""

    id: str
    title: str
    category: str = "历史告警处理记录"
    content: str = ""
    source: str = ""  # 来源（系统/链接/作者）
    version: int = 1
    updated: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class KnowledgeStore(ABC):
    @abstractmethod
    def all(self) -> list[KnowledgeDoc]: ...

    @abstractmethod
    def get(self, doc_id: str) -> KnowledgeDoc | None: ...

    @abstractmethod
    def create(self, title: str, category: str, content: str, source: str) -> KnowledgeDoc: ...

    @abstractmethod
    def update(self, doc_id: str, fields: dict[str, Any]) -> KnowledgeDoc | None: ...

    @abstractmethod
    def remove(self, doc_id: str) -> bool: ...


class InMemoryKnowledgeStore(KnowledgeStore):
    def __init__(self) -> None:
        self._docs: dict[str, KnowledgeDoc] = {}
        self._seq = 0

    def all(self) -> list[KnowledgeDoc]:
        return list(self._docs.values())

    def get(self, doc_id: str) -> KnowledgeDoc | None:
        return self._docs.get(doc_id)

    def create(self, title: str, category: str, content: str, source: str) -> KnowledgeDoc:
        self._seq += 1
        doc_id = f"KB-{self._seq:04d}"
        doc = KnowledgeDoc(
            id=doc_id,
            title=title,
            category=category if category in CATEGORIES else CATEGORIES[0],
            content=content,
            source=source,
            updated=_now(),
        )
        self._docs[doc_id] = doc
        return doc

    def update(self, doc_id: str, fields: dict[str, Any]) -> KnowledgeDoc | None:
        doc = self._docs.get(doc_id)
        if doc is None:
            return None
        data = doc.model_dump()
        for key in ("title", "category", "content", "source"):
            if key in fields and fields[key] is not None:
                data[key] = fields[key]
        data["version"] = doc.version + 1
        data["updated"] = _now()
        updated = KnowledgeDoc(**data)
        self._docs[doc_id] = updated
        return updated

    def remove(self, doc_id: str) -> bool:
        return self._docs.pop(doc_id, None) is not None


class PgKnowledgeStore(KnowledgeStore):
    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS knowledge_docs ("
                "id text PRIMARY KEY, title text, category text, content text, "
                "source text, version integer DEFAULT 1, updated text)"
            )

    def _row(self, r: Any) -> KnowledgeDoc:
        return KnowledgeDoc(id=r[0], title=r[1], category=r[2], content=r[3], source=r[4], version=r[5], updated=r[6])

    def all(self) -> list[KnowledgeDoc]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT id,title,category,content,source,version,updated FROM knowledge_docs ORDER BY id"
            ).fetchall()
        return [self._row(r) for r in rows]

    def get(self, doc_id: str) -> KnowledgeDoc | None:
        with self._pool.connection() as conn:
            r = conn.execute(
                "SELECT id,title,category,content,source,version,updated FROM knowledge_docs WHERE id=%s",
                (doc_id,),
            ).fetchone()
        return self._row(r) if r else None

    def create(self, title: str, category: str, content: str, source: str) -> KnowledgeDoc:
        cat = category if category in CATEGORIES else CATEGORIES[0]
        with self._pool.connection() as conn:
            row = conn.execute("SELECT count(*) FROM knowledge_docs").fetchone()
            doc_id = f"KB-{(int(row[0]) if row else 0) + 1:04d}"
            updated = _now()
            conn.execute(
                "INSERT INTO knowledge_docs (id,title,category,content,source,version,updated) "
                "VALUES (%s,%s,%s,%s,%s,1,%s)",
                (doc_id, title, cat, content, source, updated),
            )
        return KnowledgeDoc(id=doc_id, title=title, category=cat, content=content, source=source, updated=updated)

    def update(self, doc_id: str, fields: dict[str, Any]) -> KnowledgeDoc | None:
        cur = self.get(doc_id)
        if cur is None:
            return None
        data = cur.model_dump()
        for key in ("title", "category", "content", "source"):
            if key in fields and fields[key] is not None:
                data[key] = fields[key]
        data["version"] = cur.version + 1
        data["updated"] = _now()
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE knowledge_docs SET title=%s,category=%s,content=%s,source=%s,version=%s,updated=%s WHERE id=%s",
                (
                    data["title"],
                    data["category"],
                    data["content"],
                    data["source"],
                    data["version"],
                    data["updated"],
                    doc_id,
                ),
            )
        return KnowledgeDoc(**data)

    def remove(self, doc_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM knowledge_docs WHERE id=%s", (doc_id,))
            return bool(cur.rowcount)


def build_knowledge_store(database_url: str = "") -> KnowledgeStore:
    if database_url:
        try:
            return PgKnowledgeStore(database_url)
        except Exception:
            pass
    return InMemoryKnowledgeStore()

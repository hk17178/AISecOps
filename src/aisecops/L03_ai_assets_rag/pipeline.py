"""L03 · RAG 流水线门面（KnowledgeBase）。

把 Chunking → Embedding → VectorStore（Retriever）→ Reranker（C-7）串成一条：
- `add_doc/update_doc/remove_doc`：知识库 CRUD，同时维护向量索引（写时索引）。
- `search`：query → 向量召回 Top-N → Reranker 重排 → Top-K，**每条带 doc_id/title 引用**（C-24）。

Agent（Triage/Investigation）经此做检索增强：让 LLM 在"有出处的本地知识"上归纳，抑制幻觉。
"""

from __future__ import annotations

from pydantic import BaseModel

from .chunking import chunk_text
from .embedding import Embedder, HashingEmbedder
from .knowledge_store import KnowledgeDoc, KnowledgeStore, build_knowledge_store
from .reranker import LexicalReranker
from .vector_store import VectorRecord, VectorStore, build_vector_store


class RetrievedChunk(BaseModel):
    """一条检索命中（带出处，供引用 C-24）。"""

    doc_id: str
    title: str
    category: str
    text: str
    score: float


class KnowledgeBase:
    """知识库 + RAG 检索门面。"""

    def __init__(
        self,
        store: KnowledgeStore,
        vectors: VectorStore,
        embedder: Embedder | None = None,
        reranker: LexicalReranker | None = None,
    ) -> None:
        self.store = store
        self.vectors = vectors
        self.embedder = embedder or HashingEmbedder()
        self.reranker = reranker or LexicalReranker()

    # ---- 索引维护 ----
    def _index(self, doc: KnowledgeDoc) -> None:
        """（重）建一篇文档的向量索引：先清旧块，再切块+向量化入库。"""
        self.vectors.clear_doc(doc.id)
        records: list[VectorRecord] = []
        for i, chunk in enumerate(chunk_text(f"{doc.title}\n{doc.content}")):
            records.append(
                VectorRecord(
                    doc_id=doc.id,
                    chunk_id=f"{doc.id}#{i}",
                    text=chunk,
                    vector=self.embedder.embed(chunk),
                    meta={"title": doc.title, "category": doc.category},
                )
            )
        if records:
            self.vectors.add(records)

    def add_doc(self, title: str, category: str, content: str, source: str = "") -> KnowledgeDoc:
        doc = self.store.create(title, category, content, source)
        self._index(doc)
        return doc

    def update_doc(self, doc_id: str, fields: dict) -> KnowledgeDoc | None:
        doc = self.store.update(doc_id, fields)
        if doc is not None:
            self._index(doc)
        return doc

    def remove_doc(self, doc_id: str) -> bool:
        ok = self.store.remove(doc_id)
        if ok:
            self.vectors.clear_doc(doc_id)
        return ok

    def reindex_all(self) -> int:
        """全量重建索引（换 embedder / 修复用）。返回索引文档数。"""
        docs = self.store.all()
        for doc in docs:
            self._index(doc)
        return len(docs)

    # ---- 检索 ----
    def search(self, query: str, top_k: int = 3, candidate_n: int = 10) -> list[RetrievedChunk]:
        """向量召回 candidate_n → Reranker（C-7）重排 → 取 top_k（带引用）。"""
        if not query.strip() or self.vectors.count() == 0:
            return []
        qv = self.embedder.embed(query)
        candidates = self.vectors.search(qv, candidate_n)
        reranked = self.reranker.rerank(query, candidates)
        hits: list[RetrievedChunk] = []
        for rec, score in reranked[:top_k]:
            hits.append(
                RetrievedChunk(
                    doc_id=rec.doc_id,
                    title=str(rec.meta.get("title", "")),
                    category=str(rec.meta.get("category", "")),
                    text=rec.text,
                    score=round(score, 4),
                )
            )
        return hits


def build_knowledge_base(database_url: str = "") -> KnowledgeBase:
    """组合根用：按 DATABASE_URL 装配知识库 + 向量库（仓储模式）。"""
    kb = KnowledgeBase(build_knowledge_store(database_url), build_vector_store(database_url))
    # PG 重启后向量表可能已有数据；内存态则需重建（seed 由 runtime 触发）
    return kb


def seed_demo_knowledge(kb: KnowledgeBase) -> None:
    """首启种几篇案例知识，让检索增强开箱即用（合成数据，不含真实客户信息 C-11）。"""
    if kb.store.all():
        return
    kb.add_doc(
        "勒索软件前兆处置案例（WIN-APP 系列）",
        "历史告警处理记录",
        "现象：主机短时间内大量文件被重命名为统一后缀，伴随 vssadmin delete shadows 删除卷影。"
        "研判：真威胁（勒索前兆）。处置：立即隔离主机、保留内存镜像、排查横向移动来源账号。"
        "经验：关键资产出现卷影删除命令应直接升级为高风险并触发双模型复核。",
        source="复盘归档",
    )
    kb.add_doc(
        "扫描类告警降噪经验",
        "复盘总结",
        "现象：来自内网漏扫平台的高频端口扫描告警。研判：误报（已知合规扫描）。"
        "处置：加入抑制规则（source=漏扫平台 的端口扫描）。经验：合规扫描应按来源加抑制，避免淹没真告警。",
        source="复盘归档",
    )
    kb.add_doc(
        "应急处置命令库（Windows 取证）",
        "命令库",
        "查看可疑进程：tasklist /v；查看网络连接：netstat -ano；导出安全日志：wevtutil epl Security sec.evtx；"
        "隔离前留存：先做内存与磁盘镜像再断网。",
        source="运维 SOP",
    )

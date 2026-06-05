"""L03 RAG 流水线：embedding/chunking/向量检索/Reranker(C-7) + 知识库 CRUD/检索端到端。"""

from __future__ import annotations

import math

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L03_ai_assets_rag import (
    HashingEmbedder,
    KnowledgeBase,
    build_knowledge_store,
    build_vector_store,
    chunk_text,
)

client = TestClient(app)


def test_embedder_deterministic_and_normalized() -> None:
    emb = HashingEmbedder(dim=128)
    v1 = emb.embed("勒索软件 卷影删除")
    v2 = emb.embed("勒索软件 卷影删除")
    assert v1 == v2  # 同输入同输出（C-30 友好）
    assert abs(math.sqrt(sum(x * x for x in v1)) - 1.0) < 1e-6  # L2 归一化


def test_chunking_packs_and_splits() -> None:
    assert chunk_text("") == []
    long = "段一。\n" + "x" * 1000
    chunks = chunk_text(long, size=400, overlap=80)
    assert len(chunks) >= 3 and all(len(c) <= 400 for c in chunks)


def _kb() -> KnowledgeBase:
    return KnowledgeBase(build_knowledge_store(""), build_vector_store(""))


def test_search_returns_relevant_doc_with_citation() -> None:
    kb = _kb()
    kb.add_doc("勒索软件前兆处置", "历史告警处理记录", "大量文件被加密重命名，vssadmin 删除卷影，应隔离主机", "")
    kb.add_doc("打印机缺纸告警", "故障报告", "办公室打印机缺纸，补充纸张即可，与安全无关", "")
    hits = kb.search("主机疑似勒索 卷影被删 怎么处置", top_k=1)
    assert hits and hits[0].doc_id == "KB-0001"  # 召回到勒索那篇，而非打印机
    assert hits[0].title and hits[0].score > 0  # 带出处（C-24）


def test_reranker_runs_in_pipeline() -> None:
    # 召回多于 top_k 时，Reranker(C-7) 必经：返回数受 top_k 限制且按融合分降序
    kb = _kb()
    for i in range(5):
        kb.add_doc(f"案例{i}", "复盘总结", f"横向移动 凭证滥用 案例细节 {i}", "")
    hits = kb.search("横向移动 凭证滥用", top_k=3)
    assert len(hits) == 3
    assert hits[0].score >= hits[1].score >= hits[2].score


def test_knowledge_api_crud_and_search() -> None:
    # 建文档 → 列表含它 → 检索召回 → 删除（真实可用，非假按钮）
    created = client.post(
        "/api/knowledge",
        json={
            "title": "钓鱼邮件处置经验",
            "category": "事件处理记录",
            "content": "用户点击钓鱼链接后应重置口令并排查外联",
        },
    ).json()
    doc_id = created["id"]
    listed = client.get("/api/knowledge").json()
    assert any(d["id"] == doc_id for d in listed["docs"])
    assert listed["indexed_chunks"] > 0

    hits = client.post("/api/knowledge/search", json={"query": "钓鱼 链接 口令", "top_k": 3}).json()["hits"]
    assert any(h["doc_id"] == doc_id for h in hits)

    assert client.delete(f"/api/knowledge/{doc_id}").json()["status"] == "deleted"

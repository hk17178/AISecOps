"""L01 · 知识库 router —— RAG 语料 CRUD + 检索（L03）。

知识库 CRUD 写动作经鉴权 + 审计；search 让分析师直接体验检索增强的召回与出处。
写文档即时重建索引（写时索引），删除即时清索引。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal
from aisecops.L03_ai_assets_rag import CATEGORIES

from ..auth_deps import WRITE, require_role
from ..runtime import rt

router = APIRouter()


@router.get("/api/knowledge")
async def list_knowledge() -> dict[str, Any]:
    """知识文档列表（不含正文，列表用）+ 可选分类 + 索引块数。"""
    docs = []
    for d in rt.kb.store.all():
        item = d.model_dump()
        item.pop("content", None)
        docs.append(item)
    return {"docs": docs, "categories": list(CATEGORIES), "indexed_chunks": rt.kb.vectors.count()}


@router.get("/api/knowledge/{doc_id}")
async def get_knowledge(doc_id: str) -> dict[str, Any]:
    doc = rt.kb.store.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")
    return doc.model_dump()


class DocIn(BaseModel):
    title: str
    category: str = "历史告警处理记录"
    content: str = ""
    source: str = ""


@router.post("/api/knowledge")
async def create_knowledge(body: DocIn, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """新建知识文档（即时切块+向量化入索引）。"""
    if not body.title.strip() or not body.content.strip():
        raise HTTPException(status_code=400, detail="标题与正文不能为空")
    doc = rt.kb.add_doc(body.title.strip(), body.category, body.content.strip(), body.source.strip())
    rt.ctx.audit.append(
        actor=principal.username, action="knowledge_create", target=doc.id, details={"title": doc.title}
    )
    return doc.model_dump()


class DocUpdateIn(BaseModel):
    title: str | None = None
    category: str | None = None
    content: str | None = None
    source: str | None = None


@router.put("/api/knowledge/{doc_id}")
async def update_knowledge(
    doc_id: str, body: DocUpdateIn, principal: Principal = Depends(require_role(*WRITE))
) -> dict[str, Any]:
    """编辑知识文档（即时重建该文档索引）。"""
    doc = rt.kb.update_doc(doc_id, body.model_dump(exclude_none=True))
    if doc is None:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")
    rt.ctx.audit.append(
        actor=principal.username, action="knowledge_update", target=doc_id, details={"version": doc.version}
    )
    return doc.model_dump()


@router.delete("/api/knowledge/{doc_id}")
async def delete_knowledge(doc_id: str, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    removed = rt.kb.remove_doc(doc_id)
    if removed:
        rt.ctx.audit.append(actor=principal.username, action="knowledge_delete", target=doc_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": doc_id}


class SearchIn(BaseModel):
    query: str
    top_k: int = 3


@router.post("/api/knowledge/search")
async def search_knowledge(body: SearchIn, _: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """检索：向量召回 → Reranker(C-7) 重排 → Top-K（带出处 C-24）。"""
    hits = rt.kb.search(body.query, top_k=max(1, min(10, body.top_k)))
    return {"query": body.query, "hits": [h.model_dump() for h in hits]}

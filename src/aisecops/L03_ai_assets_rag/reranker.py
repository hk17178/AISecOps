"""L03 · 重排（Reranker）—— C-7 业界 SOTA 必备件。

向量召回只看语义相似，易"主题漂移"（召回看着像但不切题的块）。Reranker 对召回候选用
**query↔候选的词项重叠**（类 BM25/Jaccard 的交叉特征）重新打分，与向量分加权融合后重排，
纠正漂移、把真正切题的块顶上来。离线确定性；生产可换 cross-encoder（接口不变）。

缺 Reranker 的 RAG 按 CONSTRAINTS C-7 直接退回——本层把它作为必经阶段。
"""

from __future__ import annotations

from .embedding import tokenize
from .vector_store import VectorRecord


class LexicalReranker:
    """词项重叠 × 向量分的交叉重排。"""

    def __init__(self, alpha: float = 0.5) -> None:
        # alpha：向量分权重；(1-alpha)：词项重叠权重
        self.alpha = alpha

    def rerank(self, query: str, candidates: list[tuple[VectorRecord, float]]) -> list[tuple[VectorRecord, float]]:
        """对 (记录, 向量分) 候选重排，返回 (记录, 融合分) 降序。"""
        q_tokens = set(tokenize(query))
        out: list[tuple[VectorRecord, float]] = []
        for rec, vscore in candidates:
            c_tokens = set(tokenize(rec.text))
            inter = len(q_tokens & c_tokens)
            union = len(q_tokens | c_tokens) or 1
            jaccard = inter / union
            fused = self.alpha * max(0.0, vscore) + (1 - self.alpha) * jaccard
            out.append((rec, fused))
        out.sort(key=lambda x: -x[1])
        return out

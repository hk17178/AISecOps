"""L03 · RAG Pipeline（检索增强）。

Embedding → Chunking → VectorStore(Retriever) → Reranker(C-7) → KnowledgeBase 门面。
默认离线确定性实现（hashing 向量 + 词项重排），仓储模式（PG/内存）。
对外只暴露 KnowledgeBase + build/seed，Agent 与路由经它做检索增强。
"""

from .chunking import chunk_text
from .embedding import Embedder, HashingEmbedder, tokenize
from .knowledge_store import (
    CATEGORIES,
    KnowledgeDoc,
    KnowledgeStore,
    build_knowledge_store,
)
from .pipeline import (
    KnowledgeBase,
    RetrievedChunk,
    build_knowledge_base,
    seed_demo_knowledge,
)
from .reranker import LexicalReranker
from .vector_store import VectorRecord, VectorStore, build_vector_store

__all__ = [
    "Embedder",
    "HashingEmbedder",
    "tokenize",
    "chunk_text",
    "VectorRecord",
    "VectorStore",
    "build_vector_store",
    "LexicalReranker",
    "KnowledgeDoc",
    "KnowledgeStore",
    "build_knowledge_store",
    "CATEGORIES",
    "KnowledgeBase",
    "RetrievedChunk",
    "build_knowledge_base",
    "seed_demo_knowledge",
]

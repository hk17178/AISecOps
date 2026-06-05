# L03 · AI 资产层 — RAG 流水线 (RAG Pipeline)

## 职责
把"非结构化知识 + 历史事件"变成 Agent 可检索的上下文。本层只负责检索流水线，模型与知识本体在 L04。

## 子组件
- **Embedding** —— 文本/日志向量化（多语言模型选择）
- **Chunking** —— 分块策略（语义/结构感知）
- **Retriever** —— 向量检索 / BM25 / 混合检索
- **Reranker** —— **关键加分项**，业界 SOTA 必备，Cross-encoder 重排
- **Chatbot Manager** —— 对话上下文与轮次管理

## 业界对标
- LlamaIndex / LangChain RAG 流水线
- Microsoft Security Copilot 的 plugin retrieval

## 当前状态
🟢 已实现 —— 完整 RAG 流水线（离线确定性，仓储模式 PG/内存）：
- **Embedding**：`HashingEmbedder`（hashing 向量，零依赖、可复现；接口可换真模型）
- **Chunking**：`chunk_text`（按段聚合 + 超长带重叠硬切）
- **Retriever**：`VectorStore`（余弦 Top-N，内存/PG）
- **Reranker（C-7 必备★）**：`LexicalReranker`（词项重叠 × 向量分融合重排，必经阶段）
- **KnowledgeBase 门面**：知识库 CRUD（写时索引）+ `search`（召回→重排→带出处 C-24）

已接入：Triage Agent 检索增强（召回历史处置经验，带 [KB-xxxx] 引用）；
`/api/knowledge` CRUD + `/api/knowledge/search` 真实可用。语料分类见
[知识库蓝本](../../../docs/specs/knowledge-base.md)。CMDB 等结构化数据按 C-25 走工具直查，不入此库。
后续：接 L05 真 embedding 模型、Chatbot Manager 多轮、前端知识库管理页。

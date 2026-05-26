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
🟡 占位 —— 仅目录与本说明，未实现

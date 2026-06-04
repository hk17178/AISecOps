# ADR-0006 · Agent 编排自研（不引 LangGraph/LangChain Agents）

- 状态：Accepted
- 日期：2026-06-04
- 决策者：muzi
- 来源：正式化 [technical-design §3.2](../specs/technical-design.md) 已定选型

## 背景

L02 需要 Orchestrator + 多个 Agent 角色（C-5：禁止扁平 Agent，必须有 Orchestrator）。编排层候选：自研 / LangGraph / LangChain Agents。

## 决策

**Agent 编排自研**（轻量 Orchestrator + `Agent` 基类）。

- 自用规模小，LangGraph 偏重、抽象多、升级易破坏，自研更可控。
- 自研能精确落实本项目铁律：abstain（C-26）、双模型 cross-check（C-27）、引用必附（C-24）、审计链（C-23）——这些在通用框架里要绕。
- 接口已在 [technical-design §3.6](../specs/technical-design.md) 定义：`Agent.run(task, ctx)`，ctx 注入 memory/llm(L05)/mcp_registry(L06)/audit(L12)。

不自造轮子的部分仍复用成熟库：LLM 调用经 L05、RAG 用 LlamaIndex、schema 用 Pydantic。

## 后果

**正面**：轻、可控、铁律落地直接、无框架锁定。
**负面**：要自己实现调度/重试/状态（但范围小）。
**风险**：未来 Agent 复杂度上升时自研成本增加 → 接口稳定的前提下可局部替换为框架。

## 关联

- [technical-design §3.2/§3.6](../specs/technical-design.md) · CONSTRAINTS C-5/C-24/C-26/C-27 · [ADR-0008 跨层 DAG](0008-cross-layer-dependency-dag.md)

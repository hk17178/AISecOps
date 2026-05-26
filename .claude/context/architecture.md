# 12 层架构精炼版（给 AI 用的速查）

> 视觉权威是 [`docs/architecture-v2.md`](../../docs/architecture-v2.md)（V2 文字版含 ASCII 图），本文是给 AI 的更精简速查。
> 冲突时以 V2 为准。V1 `docs/architecture.png` 已过时，见 [ADR-0002](../../docs/adr/0002-architecture-v2-supersedes-png.md)。

## 自上而下 12 层

```
┌─────────────────────────────────────────────────────────┐
│ L01 人机交互层  告警面板/工单 UI/报表 UI/Chat 面板         │
├─────────────────────────────────────────────────────────┤
│ L02 AI Agent 群 + 平台核心管控                            │
│   ├─ Orchestrator (调度)                                 │
│   ├─ Triage / Investigation / Enrichment                │
│   ├─ Responder / Reporter / Intel / Tuning              │
│   └─ Platform Core: IAM / 工单 / Memory / Prompt 治理     │
├─────────────────────────────────────────────────────────┤
│ L03 RAG 流水线  Embedding/Chunking/Retriever/Reranker    │
├─────────────────────────────────────────────────────────┤
│ L04 模型与知识  LLM / DSLM / Skills(SOP) / Prompts / KG  │
├─────────────────────────────────────────────────────────┤
│ L05 Gateway    LLM Gateway + API Gateway                │
├─────────────────────────────────────────────────────────┤
│ L06 MCP Server 群  安全工具/数据源/协议/厂商/AIOps/自定义  │
├─────────────────────────────────────────────────────────┤
│ L07 SecOps 业务能力  分诊/调查/狩猎/SOAR/UEBA/漏洞合规    │
├─────────────────────────────────────────────────────────┤
│ L08 智能分析引擎                                          │
│   ├─ 通用：异常/关联/根因/聚类/容量/基线/知识抽取          │
│   └─ 安全：攻击图/Kill Chain/IoC/UEBA/失陷研判             │
├─────────────────────────────────────────────────────────┤
│ L09 数据中台  Ingest/中转池/ETL/特征/数据湖               │
├─────────────────────────────────────────────────────────┤
│ L10 数据采集  Agent/Log/Trace/Metric/Sensors             │
├─────────────────────────────────────────────────────────┤
│ L11 被管对象  数据库/安全资产/AI 合规/云资源/流量          │
├─────────────────────────────────────────────────────────┤
│ L12 核心支撑  资产识别/调度/可观测/凭证                   │
└─────────────────────────────────────────────────────────┘
```

## 数据流（自下而上）

```
L10 采集 → L09 中台归一化 → L08 算法分析 ↘
                                          → L02 Agent 决策 → L07 业务出口 → L01 UI
L04 模型 + L03 RAG ↗                       ↑
L06 MCP（外部工具）─────────────────────────┘
L05 Gateway 横切所有 LLM/API 调用
L12 横切所有层（调度、凭证、可观测）
```

## 跨层调用规则

✅ **允许**：相邻层直接调用，向上经接口
❌ **禁止**：跨层直连（如 L07 → L10 跳过 L09）
✅ **L05 Gateway 例外**：所有层调用 LLM 都必须经 L05
✅ **L06 MCP 例外**：L02/L07/L08 可直接通过 MCP 调外部工具

## 业界对标速查（用于决策）

| 我们在做 | 对标谁的什么模块 | 关键差异化 |
|---|---|---|
| L02 Multi-Agent | Charlotte Team Leader / QAX-GPT 调度 | 必须有 Tuning Agent 形成飞轮 |
| L04 DSLM | Charlotte 训练自 Falcon MDR 数据 | 国产场景，需从客户日志构建 |
| L05 LLM Gateway | LiteLLM / Microsoft Copilot | 必须支持国产 LLM（豆包/通义/智谱） |
| L06 MCP | Microsoft 300+ 连接器 / Anthropic MCP | 安全工具 MCP 是差异化战场 |
| L07 SOAR | Charlotte Agentic SOAR | HITL 必须默认开启 |
| L08 攻击图 | 阿里云图计算 + 大模型溯源 | 必须含国内攻击者 TTP 库 |
| L11 AI 合规 | CrowdStrike Shadow AI 治理 | 2026 新基线必备 |

## 当前实现状态（每层一行）

| 层 | 状态 |
|---|---|
| L01 ~ L12 | 🟡 全部占位，仅 README + `__init__.py` |

## P0 实现优先级

1. L05 LLM Gateway（其他层依赖它）
2. L02 Orchestrator + 1 个 Triage Agent
3. L06 1 个 MCP Server（数据源类，比如 Syslog）
4. L07 alert_triage（端到端 demo）

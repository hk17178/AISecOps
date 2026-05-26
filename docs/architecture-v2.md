# AISecOps 架构 V2 · 文字权威版

> ⚠️ **本文件是当前视觉权威**（取代 V1 `architecture.png`）。
> 冲突时一律以本文为准。
> V1 PNG 状态：**Superseded by V2** —— 保留作历史参考，请勿再据此设计。
> 用户后续会按 V2 重画 PNG；新 PNG 完成后，本文继续作为文字权威。

> 详细背景见 [ADR-0002](adr/0002-architecture-v2-supersedes-png.md)。

---

## V2 vs V1 变更摘要

| # | V1 PNG 问题 | V2 修正 |
|---|---|---|
| ① | L7 标签 "AIOps Capabilities × 用户价值场景" | **改为 "AISecOps Capabilities"**，显式列 6 大 SEC 场景 |
| ② | L8 只有 AIOps 算法（异常/根因/容量/基线） | **新增"安全分析半边"**：attack_graph / kill_chain / ioc_correlation / ueba_analytics / compromise_judgment |
| ③ | L4 只标 "大模型 LLM" | **新增 DSLM 框**：log_classifier / payload_detector / fp_suppressor |
| ④ | L2 只有"工单引擎"（人工流转） | **新增 SOAR Playbook 引擎**（自动化处置剧本），与工单引擎并列且明确区分 |
| ⑤ | 没有反馈飞轮箭头 | **新增数据流**：L1 工单/报表 → L2 Tuning Agent → L4 DSLM 再训练 |
| ⑥ | L3 / L4 都叫 "AI 资产层"，混淆 | **L3 重命名 "RAG Pipeline"**、**L4 重命名 "Models & Knowledge"** |
| ⑦ | L12 内容模糊（资产标识/资产识别/调度集群） | **L12 显式四件套**：asset_cmdb / scheduling / secrets / observability |
| ⑧ | HITL 通道隐藏 | **显式画出 HITL Channel**：横切 L02/L07，连接 L01 工单 UI |

---

## 12 层总览（ASCII 图）

```
┌──────────────────────────────────────────────────────────────────┐
│ L01 人机交互     告警面板 │ 工单 UI │ 报表 UI │ Chat 面板        │
├──────────────────────────────────────────────────────────────────┤
│ L02 AI Agent 群 + 平台核心管控                                    │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │ Orchestrator (调度，禁省略)                              │    │
│   └──┬────────┬────────┬────────┬────────┬────────┬────────┘    │
│      ▼        ▼        ▼        ▼        ▼        ▼              │
│   Triage  Invest.  Enrich.  Responder Reporter  Intel   Tuning  │
│                                                                  │
│   Platform Core: IAM │ 工单引擎 │ ★SOAR Playbook │ Memory       │
│                  Prompt 治理 │ 通知中枢                          │
│                              │                                   │
│       ╔══════════════════════▼═══════════════════════╗           │
│       ║  HITL Channel (横切 L02 + L07，写操作必经)    ║           │
│       ╚══════════════════════════════════════════════╝           │
├──────────────────────────────────────────────────────────────────┤
│ L03 RAG Pipeline   Embedding │ Chunking │ Retriever │ Reranker  │
│                    Chatbot Manager                               │
├──────────────────────────────────────────────────────────────────┤
│ L04 Models & Knowledge                                           │
│   ┌──────────────┐  ┌─────────────────┐                          │
│   │  LLM 群      │  │ ★DSLM 群        │                          │
│   │ 豆包/通义/   │  │ log_classifier  │                          │
│   │ 智谱/Claude  │  │ payload_detector│                          │
│   │              │  │ fp_suppressor   │                          │
│   └──────────────┘  └─────────────────┘                          │
│   Skills(SOP) │ Prompts │ Memory │ Knowledge Graph │ 资产库      │
├──────────────────────────────────────────────────────────────────┤
│ L05 Gateway       LLM Gateway │ API Gateway                      │
│                   (所有 LLM/API 调用必经)                         │
├──────────────────────────────────────────────────────────────────┤
│ L06 MCP Server 群                                                │
│   security_tools │ data_sources │ protocols │ vendors            │
│   │ aiops │ custom                                               │
├──────────────────────────────────────────────────────────────────┤
│ L07 ★AISecOps Capabilities (业务能力出口)                         │
│   alert_triage │ investigation │ threat_hunting                  │
│   │ soar_playbooks │ ueba │ vuln_compliance                      │
├──────────────────────────────────────────────────────────────────┤
│ L08 Analytics Engines                                            │
│   ┌─────────────────────┐  ┌─────────────────────────────┐       │
│   │ AIOps 算法          │  │ ★安全分析算法 (Security)      │       │
│   │ anomaly_detection   │  │ attack_graph                │       │
│   │ correlation         │  │ kill_chain                  │       │
│   │ root_cause          │  │ ioc_correlation             │       │
│   │ clustering          │  │ ueba_analytics              │       │
│   │ capacity_prediction │  │ compromise_judgment         │       │
│   │ performance_baseline│  │                             │       │
│   │ knowledge_extraction│  │                             │       │
│   └─────────────────────┘  └─────────────────────────────┘       │
├──────────────────────────────────────────────────────────────────┤
│ L09 Data Platform  ingest │ transit │ etl │ feature_store        │
│                    data_lake │ eda                               │
├──────────────────────────────────────────────────────────────────┤
│ L10 Data Collection                                              │
│   agents │ log │ trace │ metric │ sensors                        │
├──────────────────────────────────────────────────────────────────┤
│ L11 Target Estate                                                │
│   databases │ security_assets │ ai_compliance                    │
│   │ cloud_resources │ network_traffic                            │
├──────────────────────────────────────────────────────────────────┤
│ L12 Core Support                                                 │
│   ★asset_cmdb │ scheduling │ ★secrets │ ★observability            │
└──────────────────────────────────────────────────────────────────┘

★ = V2 相对 V1 的新增 / 修正点
```

---

## 数据流（含反馈飞轮）

```
┌─ 正向数据流（自下而上）──────────────────────────────────────┐
│                                                              │
│  L11 Target → L10 采集 → L09 中台 → L08 算法分析             │
│                                          │                   │
│                                          ▼                   │
│   L04 模型/知识 + L03 RAG ─────► L02 Agent 决策              │
│         ▲                              │                     │
│         │                              ▼                     │
│         │                       L07 业务出口                  │
│         │                              │                     │
│   L06 MCP ◄──── 工具调用 ◄────────────┤                     │
│   L05 Gateway ◄── LLM 调用 ◄──────────┤                     │
│                                        ▼                     │
│                              ┌─────────────────┐             │
│                              │ HITL Channel    │             │
│                              │ (写操作必经)     │             │
│                              └─────────┬───────┘             │
│                                        ▼                     │
│                                  L01 UI / 工单                │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌─ ★反馈飞轮（V2 新增，自上而下）─────────────────────────────┐
│                                                              │
│  L01 工单决策 / 报表标注                                      │
│    │ (分析师"确认 / 否决 / 修正"研判)                         │
│    ▼                                                         │
│  L02 Tuning Agent (周期消费反馈)                              │
│    │                                                         │
│    ▼                                                         │
│  L04 DSLM 再训练 / Prompt 调优 / KG 富化                      │
│    │                                                         │
│    └──► 下一轮 L02 Agent 决策更准                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 跨层调用规则（与 CONSTRAINTS C-13 一致）

✅ **允许**
- 相邻层调用
- 任何层经 **L05 Gateway** 调 LLM
- 任何层经 **L06 MCP** 调外部工具
- 任何层依赖 **L12 横切支撑**（凭证 / 可观测 / 调度）

❌ **禁止**
- 跨层直连（如 L07 → L10 跳过 L09）
- 反向调用（如 L09 调 L07）—— 飞轮反馈是**事件驱动**，不算反向直连
- L05 / L06 之外的 LLM / 外部工具调用

⚠️ **HITL Channel 特别说明**
- 横切层概念，**不是独立层**
- L02 Responder Agent / L07 SOAR Playbook 的写操作必须经过
- 实现在 L02 platform_core，UI 在 L01

---

## 每层精炼说明（V2 修正后）

### L01 · 人机交互
- 4 个面板：告警 / 工单 / 报表 / Chat
- 与 V1 一致

### L02 · AI Agent 群 + 平台核心管控（★ 含 SOAR Playbook + HITL Channel）
- **7 + 1 Agent 角色**：Orchestrator(必备) + Triage / Investigation / Enrichment / Responder / Reporter / Intel / Tuning
- **Platform Core**：IAM / 工单引擎 / **★SOAR Playbook 引擎**（自动剧本，与工单引擎并列但职责不同）/ Memory Store / Prompt 治理 / 通知中枢
- **★HITL Channel**：横切层，写操作必经

### L03 · ★ RAG Pipeline（原"AI 资产层"）
- Embedding / Chunking / Retriever / **Reranker（必备）** / Chatbot Manager

### L04 · ★ Models & Knowledge（原"AI 资产层"）
- **LLM 群**：豆包 / 通义 / 智谱 / Claude（国产优先）
- **★ DSLM 群**：log_classifier / payload_detector / fp_suppressor（业界基线必备）
- Skills 库(SOP) / Prompts / Memory / Knowledge Graph / 资产库

### L05 · Gateway
- LLM Gateway + API Gateway
- 所有 LLM/API 调用必经

### L06 · MCP Server 群
- 6 类：security_tools / data_sources / protocols / vendors / aiops / custom

### L07 · ★ AISecOps Capabilities（原"AIOps Capabilities"）
- **6 大 SEC 出口**：alert_triage / investigation / threat_hunting / soar_playbooks / ueba / vuln_compliance
- 与 V1 最关键的差异

### L08 · ★ Analytics Engines（新增安全分析半边）
- **AIOps 算法**（保留 V1）：anomaly_detection / correlation / root_cause / clustering / capacity_prediction / performance_baseline / knowledge_extraction
- **★ 安全分析算法**：attack_graph / kill_chain / ioc_correlation / ueba_analytics / compromise_judgment

### L09 · Data Platform
- ingest / transit / etl / feature_store / data_lake / eda
- 与 V1 一致

### L10 · Data Collection
- agents / log / trace / metric / sensors
- 与 V1 一致

### L11 · Target Estate
- databases / security_assets / ai_compliance / cloud_resources / network_traffic
- 与 V1 一致

### L12 · ★ Core Support（V1 内容模糊，V2 明确四件套）
- **asset_cmdb**（替代 V1 的"资产标识/资产识别"重复项）
- **scheduling**（任务/资源/Agent 调度）
- **★ secrets**（Vault 集成；CONSTRAINTS C-9 凭证零硬编码的实现位置）
- **★ observability**（Trace/Metric/Log；PRINCIPLES P-13 可观测性内建的实现位置）

---

## 关联文件

- [ADR-0001 采用 12 层架构作为基线](adr/0001-architecture-baseline.md)
- [ADR-0002 V2 取代 V1 PNG 成为视觉权威](adr/0002-architecture-v2-supersedes-png.md)
- [CONSTRAINTS.md](../CONSTRAINTS.md)（C-15 视觉权威条款已更新指向本文）
- [PRINCIPLES.md](../PRINCIPLES.md)
- [V1 PNG 历史存档](architecture.png) ⚠️ 已过时，仅作参考

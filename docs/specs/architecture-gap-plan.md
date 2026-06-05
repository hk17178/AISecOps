# 架构补齐开发计划（对照 architecture-v2）

> 缘起：硬铁律已全清、业务闭环已通，但 architecture-v2 里**规划好却没建**的元素仍有一批；
> 用户反馈的 8 个问题几乎精准命中这些未建元素。本计划把"纵向加固"切回"横向补齐架构广度"。
> 权威：[architecture-v2](../architecture-v2.md) · [CONSTRAINTS](../../CONSTRAINTS.md) · [ADR-0003 自用定位](../adr/0003-self-use-positioning.md)。
> 决策（2026-06-05）：先做 **Phase 1 智能闭环**；AD 集成纳入但排后（Phase 5）；本文档先行评审。

## 0. 用户 8 问 → 架构落点映射

| # | 用户问题 | architecture-v2 落点 | 现状 | 判定 | Phase |
|---|---|---|---|---|---|
| ⑧ | 故障记录自动沉淀知识库+回流 | **★反馈飞轮 + L02 Tuning Agent** | 飞轮断裂，知识库只能手填 | V2 核心未建 | **1** |
| ① | Agent 不能编排/管理/新建 | **L02 7+1 Agent 群** | 只编了 3/8，UI 只配不增 | 真缺口 | **1** |
| ⑤ | Prompt 改了不进 Agent（热加载） | L04 Prompt 治理 | save 不热加载 | 真缺口（飞轮前置） | **1** |
| ⑦ | 缺驾驶舱（谁在处理/进展/SLA） | L01 + HITL Channel + 工单流 | 工单无 assignee/进度/SLA | 真缺口（**需改 V2+ADR**） | 2 |
| ⑥ | 域控 AD 登录 + 工单派发到 AD 账号 | L02 IAM + L06 protocols(LDAP) | 无 | 合理，排后 | 5 |
| ② | 日志多源接入（ES/Zabbix/…） | L10 采集 + L06 data_sources | 仅 ES 薄适配器 | 已声明延后(ADR-0009)，现激活 | 3 |
| ③ | Skills 管理 | **L04 Skills(SOP)** | 零代码 | 真缺口（**需 ADR 定边界**） | 3 |
| ④ | 仪表盘内容匮乏 | L01 | 5 数+最新告警 | 真该补 | 4 |
| ⑤ | Prompt 新建/删除 CRUD | L04 | 只能改已有 key | 真缺口 | 4 |

---

## Phase 1 · 智能闭环（反馈飞轮 + Agent 群补全）★本期

> 目标：让"处理过的案子"自动变成"下次处理得更准"，并把 7+1 Agent 群补成真。
> 这是 architecture-v2 的 ★反馈飞轮，且接着已建好的 L03 RAG（Triage 已会自动召回）。

### 1.1 Prompt 热加载进 Agent（飞轮前置，⑤的一半）
- **落点**：L02 Agent ← L04 PromptStore（编排层读知识，DAG 合规）。
- **现状**：Triage/Investigation/Correlation 用硬编码 `_SYSTEM`，UI 改 prompt 不生效。
- **目标**：Agent 启动/每次 run 从 `ctx`（注入 PromptStore）读 active 版本，缺失回退硬编码默认。
- **改动**：`L02_agents/base.py`(AgentContext 加 prompts) · 三个 agent 的 `_SYSTEM` 改为 `_system(ctx)` · `runtime.py` 注入 · `agent_config` 的 `prompt_key` 启用。
- **DoD**：UI 改 triage system prompt → `/api/triage` 行为随之变；无 store 时回退默认、测试不破。
- **ADR**：否。

### 1.2 补齐 7+1 Agent（①）
> 每个都必须是**真实现**（C-4，禁纯 Prompt 包装），经 Orchestrator 路由（C-5）。

| Agent | 真实质（非纯 LLM） | 复用 | 落点 |
|---|---|---|---|
| **Enrichment** | 确定性富化：CMDB 资产 + IoC 命中 + 历史处理(RAG) 聚合成上下文 | 现 triage 内联逻辑抽出 | L02 |
| **Responder** | 写处置必经 HITL：建工单→批准→（占位/真实）经 L06 下发 | 现 SOAR/ticket 流 | L02 |
| **Reporter** | 确定性取数 + LLM 叙述（已有 ReportingService） | 包装为 Agent | L02 |
| **Intel** | IoC 匹配 + 情报富化（查而非记忆 C-25） | 现 match_iocs | L02 |
| **Tuning** | 消费"结案反馈事件"→沉淀知识 + 阈值调优（见 1.3） | 新建 | L02 |
- **改动**：`L02_agents/{enrichment,responder,reporter,intel,tuning}.py` · Orchestrator 注册 · `routers/agents.py` 名册改为真实 status · runtime 装配。
- **DoD**：`_AGENT_ROSTER` 全部"实现"且经 Orchestrator 可路由；Agent 页显示每个 agent 真实配置；各 agent 有测试。
- **ADR**：否（在 V2 既有 7+1 范围内）。

### 1.3 反馈飞轮：结案自动沉淀知识 + 回流（⑧，核心）
- **落点**：L01 结案 ──事件──▶ L02 Tuning Agent ──▶ L03 知识库（V2 飞轮唯一合法"向上"，事件驱动）。
- **现状**：断裂。知识库手填；Triage 已会自动 RAG 召回（回流的"消费端"已就位）。
- **目标**：
  1. 工单结案 / 调查产出真结论 / 关联确认事件 时，发"反馈事件"；
  2. **Tuning Agent** 消费 → 把"现象→研判→处置→复盘"结构化写入 L03 知识库（category=历史告警处理记录/事件处理记录，source=工单/调查 ID，去重）；
  3. 下一轮 Triage/Investigation 自动召回（已通）→ 飞轮闭合；
  4. （轻量）Tuning 统计误报/漏报反馈，给阈值调整**建议**（不自动改，留人确认）。
- **改动**：`L02_agents/tuning.py`(Tuning Agent) · `L02_agents/feedback.py`(反馈事件 + 内存队列/同步 hook) · 在 `routers/tickets.py`(结案)、`routers/investigation.py`(events/confirm) 发事件 · runtime 串接 · 知识库去重。
- **DoD**：审批一个真威胁工单 → 知识库自动多一篇带 source 的案例 → 再分诊相似告警时 `<kb>` 召回到它（端到端测试）。
- **ADR**：否（V2 飞轮已画，本期落地）。可加一篇"飞轮落地说明"ADR 记录事件驱动实现选择。

### 1.4 前端
- Agent 页：从"3 实现 5 规划"变"8 实现"，展示每个 agent 配置 + 所属编排链。
- 知识库页：新增"自动沉淀"来源标识（区分人工/飞轮）。

---

## Phase 2 · 协作驾驶舱（⑦ + ⑥的工单派发半边）
- **需先改 V2 文字版 + 写 ADR**（C-15：驾驶舱是 L01 新视图，V2 未显式画）。
- 工单模型扩展：`assignee / progress / sla_due / 处理时间线`。
- 驾驶舱页：实时看板——每个故障/事件指派给谁、状态、进展、超时预警；MTTD/MTTR；管理层只读总览（少打扰技术）。
- DoD：工单可指派、可更新进度、超 SLA 标红；驾驶舱一屏看清"谁在处理啥/到哪步"。

## Phase 3 · 数据/能力底座（② + ③）
- **② 日志多源接入**：L06 data_sources 适配器框架（ES/Zabbix/Syslog/Kafka…，薄适配器优先 ADR-0004）+「日志接入管理」页（数据源 CRUD/连通/解析/状态），对标 Splunk「Data inputs」。激活 ADR-0009 留的 L10 接入。
- **③ Skills(SOP)**：**先写 ADR** 厘清 Skills(L04 SOP) vs SOAR Playbook(L02 自动化处置) vs Prompt(L04) vs 知识库(L03) 边界 → 再建 Skills 库 + Agent 调用 + 管理页。
- DoD：能在 UI 加一个 Zabbix 数据源并连通测试；Skills 可被 Agent 调用且可管理。

## Phase 4 · 可视化快赢（④ + ⑤剩余）
- **④ 仪表盘增强**，建议补：告警趋势(时序) · 按严重度/来源/Kill-Chain阶段分布 · **MTTD/MTTR** · 待研判队列+SLA · HITL 工单看板 · 失陷主机 Top · Agent 活动量 · 成本趋势 · 降噪率趋势 · 飞轮沉淀量。
- **⑤ Prompt 新建/删除 CRUD**（热加载已在 Phase 1 做）。
- DoD：仪表盘 ≥6 块真实可视化（来自真 store）；Prompt 可增删 key。

## Phase 5 · 域控 AD 集成（⑥，排后）
- L06 protocols/LDAP 适配器 + L02 IAM 联邦（AD 账号登录，映射到三角色）。
- 工单自动派发到 AD 账号（接 Phase 2 的 assignee）+ 通知到对应人。
- **需 ADR**（IAM 联邦是新依赖边/新能力）。守住 ADR-0003：单组织 AD，不做多租户。

---

## 跨期纪律
- 每块完成跑 `make check` 全绿 + 前端 tsc/build；写动作留痕(C-23)、持久化(P-18)、禁假按钮。
- 改架构的（Phase 2 驾驶舱、Phase 3 Skills、Phase 5 AD）**先改 V2 文字版 + 写 ADR 再编码**（C-15）。
- 新 Agent 必须真实现（C-4）、经 Orchestrator（C-5）、LLM 必经 Gateway（C-6）。

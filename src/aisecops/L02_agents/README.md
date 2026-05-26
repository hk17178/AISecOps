# L02 · AI Agent 群 + 平台核心管控 (Multi-Agent System + Platform Core)

## 职责
平台的"大脑"。多个专职 Agent 协同处理安全事件，配套平台级管控（IAM / 工单 / Memory / Prompt 治理 / 通知）保障可观测、可治理。

## 子组件（按业界 5+1 角色 + 国内常见扩展）
| 角色 | 业界对标 | 职责 |
|---|---|---|
| **Orchestrator** | Charlotte Team Leader / 奇安信调度 Agent | 调度、路由、任务分解 |
| **Triage Agent** | Microsoft Phishing Triage / Dropzone Triage | 告警分诊 + 误报抑制 |
| **Investigation Agent** | Charlotte Detection Triage | 事件取证 + 时间线 |
| **Enrichment Agent** | —— | 情报富化、上下文补全 |
| **Responder Agent** | Charlotte Agentic Response | 处置决策（人审后执行） |
| **Reporter Agent** | —— | 受众分级报告（管理层/技术层） |
| **Intel Agent** | TI 接入 Agent | 威胁情报关联 |
| **Tuning Agent** | —— | 模型/规则调优反馈闭环 |

## 平台核心管控 (Platform Core)
- `platform_core/iam` —— 身份、权限、租户隔离
- `platform_core/ticket` —— 工单引擎（与 SOAR Playbook 不同：人工流转）
- `platform_core/memory_store` —— Agent 长期记忆（向量 + 图）
- `platform_core/prompt_governance` —— Prompt 模板、版本、A/B、Shadow AI 监管
- `platform_core/notify` —— 邮件 / 企微 / 钉钉 / SMS / Webhook

## 业界对标
- CrowdStrike Charlotte Agentic SOAR（多 Agent 编排）
- 启明星辰 1+1+N（统一大模型 + AIDK 智能体框架 + N 产线智能体）

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

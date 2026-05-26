# 术语表 · 安全 + AI

> 写代码、起名、文档用到的术语统一。避免一个概念多名字。

## AISecOps 核心

| 术语 | 释义 | 备注 |
|---|---|---|
| **AISecOps** | AI 驱动的安全运营 | 项目自身定位，不是 AIOps |
| **SOC** | Security Operations Center 安全运营中心 | L01 + L07 的目标用户 |
| **SOAR** | Security Orchestration, Automation, Response | L07 子模块，**不是工单** |
| **SIEM** | Security Information and Event Management | L06 安全工具 MCP 接入对象 |
| **EDR / XDR / NDR** | 端点 / 扩展 / 网络 检测响应 | 同上 |
| **UEBA** | User and Entity Behavior Analytics | L08 安全分析半边 |
| **IoC** | Indicator of Compromise 失陷指标 | TI 关联用 |
| **TTP** | Tactics, Techniques, Procedures | 攻击者画像 |
| **Kill Chain** | 杀伤链（Lockheed Martin 7 阶段） | L08 必备分析模型 |
| **TI** | Threat Intelligence 威胁情报 | L02 Intel Agent |
| **HITL** | Human-in-the-Loop 人在环 | 重大动作默认必须 |
| **MTTD / MTTR** | 平均检测/响应时间 | 平台效果指标 |

## AI / Agent

| 术语 | 释义 | 备注 |
|---|---|---|
| **LLM** | 大语言模型 | L04 |
| **DSLM** | Domain-Specific LM 领域小模型 | L04，**业界基线必备** |
| **Orchestrator** | 调度 Agent | L02 顶层，禁止省略 |
| **Triage Agent** | 告警分诊 Agent | 国内有时叫"研判 Agent" |
| **RAG** | Retrieval-Augmented Generation | L03 |
| **Reranker** | RAG 重排序器 | L03 必备 SOTA 组件 |
| **MCP** | Model Context Protocol (Anthropic) | L06 协议基础 |
| **Memory Store** | Agent 长期记忆 | L02，**不是数据库** |
| **Prompt 治理** | Prompt 版本、A/B、Shadow AI 监管 | L02 |

## 容易混淆的概念

| 看起来一样 | 实际不同 | 区别 |
|---|---|---|
| L02 工单引擎 vs L07 SOAR | 工单 = 人工流转 | SOAR = 自动剧本 |
| L02 Agent vs L10 Agent | L02 = AI 智能体 | L10 = 采集端 Agent（如 Filebeat） |
| L04 Memory vs L02 Memory Store | L04 = 数据结构定义 | L02 = 运行时存储 |
| L02 Memory Store vs L09 数据湖 | Memory = Agent 上下文 | 数据湖 = 业务数据 |
| L03 Embedding vs L04 LLM Embedding | L03 = RAG 流水线一环 | L04 = 模型本身 |

## 与 itops-agent-platform 等"反模式"的术语差异

| 反模式叫法 | 本项目正确叫法 | 原因 |
|---|---|---|
| "9 个智能体" | Multi-Agent + Orchestrator | 扁平 9 个不是 Multi-Agent |
| "工作流编排" | SOAR Playbook 或工单引擎（看场景） | 不能含糊 |
| "AI 助手" | Agent 或 Copilot | 助手有歧义 |
| "运维场景" | SecOps 业务能力 / AIOps 业务能力 | 必须明确是 SEC 还是 OPS |

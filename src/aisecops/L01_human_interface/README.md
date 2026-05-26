# L01 · 人机交互层 (Human Interface)

## 职责
对外提供分析师、管理员、最终用户的可视化与对话入口，承接 SOC tier-1/tier-2 的日常操作面。

## 子组件
- **告警面板 (Alert Console)** —— 告警分诊视图，对接 L07 alert_triage
- **工单 UI (Ticket Console)** —— 安全事件工单与处置流转，对接 L02 platform_core 工单引擎
- **报表 UI (Report Console)** —— 自动报告、合规报告、MTTD/MTTR 仪表盘
- **Chat 面板 (Conversational Console)** —— 自然语言调查入口，对接 L02 Orchestrator
- **移动端 / Web Console** —— 多端响应

## 业界对标
- Microsoft Security Copilot 的 Standalone & Embedded experience
- CrowdStrike Falcon Console + Charlotte AI Chat
- 奇安信 QAX-GPT 的安全工作台

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

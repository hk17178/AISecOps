# L11 · 被管对象 (Target Estate)

## 职责
描述平台监管的对象本体。不只是"主机"——业界 AISecOps 必须覆盖五大类对象。

## 子组件
- **databases/** —— 数据库资产
- **security_assets/** —— **安全监管对象**（防火墙 / WAF / EDR / IDS / SIEM 自身）
- **ai_compliance/** —— **AI 模型合规对象**（Shadow AI 治理、模型安全审计）
- **cloud_resources/** —— 云资源（IAM / OSS / 计算 / 网络）
- **network_traffic/** —— 流量

## 业界对标
- CrowdStrike 2025 推出的 AI Agent 安全 + Shadow AI 治理
- Microsoft Purview AI 合规

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

## 为什么 AI 模型合规是 2026 新增基线
随着企业大量引入 LLM、智能体、Copilot，AI 模型本身成为攻击面。CrowdStrike 2025 已专门发布"AI Agent 安全 + Shadow AI 治理"产品线——这是 AISecOps 区别于传统 SOC 的代际特征。

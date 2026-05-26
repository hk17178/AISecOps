# L07 · AISecOps 业务能力 (SecOps Capabilities)

## 职责
平台对外的安全运营能力出口。本层与 L02 Agent 群配合，把"AI + 数据 + 工具"打包成业务场景。

> ⚠️ **重要**：本层是 AISecOps 与 AIOps 的分水岭。
> 如果只填了运维场景（容量预测/性能基线），那就是 AIOps；只有填了下列安全场景，才算 AISecOps。

## 子组件（必备 6 大 SEC 能力）
- **alert_triage/** —— 告警分诊 + 误报抑制
  - 业界基线：Microsoft 提升准确率 +77%，提速 6.5×
- **investigation/** —— 事件调查 + 自然语言取证
  - 业界基线：单告警调查时间 30-60min → 2-5min
- **threat_hunting/** —— 威胁狩猎（主动）
- **soar_playbooks/** —— SOAR 安全剧本编排（与 L02 工单引擎不同：自动化处置）
- **ueba/** —— 用户与实体行为分析（业务出口；算法在 L08）
- **vuln_compliance/** —— 漏洞管理 + 合规审计

## 业界对标
- CrowdStrike Charlotte Agentic Detection Triage / Response / Workflows
- 奇安信 QAX-GPT 告警研判（95% 准确率）
- 深信服 Omni-Command XDR

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

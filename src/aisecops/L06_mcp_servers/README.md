# L06 · MCP Server 群 — 多协议网关与工具适配

## 职责
基于 **Model Context Protocol (MCP)** 把外部工具、数据源、第三方系统适配成 Agent 可调用的标准能力。是平台扩展生态的关键层。

## 子组件
- **security_tools/** —— 安全工具 MCP
  - SIEM（Splunk / QRadar / 奇安信天眼）
  - EDR（CrowdStrike Falcon / 深信服 EDR）
  - NDR / XDR
  - 漏洞扫描（Nessus / 绿盟 RSAS）
  - 蜜罐 / WAF / IDS
- **data_sources/** —— 数据源 MCP（DB / OSS / Kafka / ES）
- **protocols/** —— 通讯协议 MCP（SSH / WinRM / SNMP / Syslog）
- **vendors/** —— 各厂商专有 API MCP
- **aiops/** —— AIOps 系列 MCP（Prometheus / Zabbix / Grafana）
- **custom/** —— 自定义 Agent 功能 MCP

## 业界对标
- Microsoft Security Copilot 的 300+ 连接器生态
- Charlotte Agentic SOAR 的第三方 Agent 编排
- Anthropic MCP 官方协议规范

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

## 为什么 MCP 是 2026 战略要点
业界 2025-2026 的核心战场是 **Agent Marketplace + MCP 连接器生态**。本层决定了平台能不能"开放"——是单体应用还是平台底座。

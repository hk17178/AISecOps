# L06 · 工具适配层 — 多协议网关与外部工具治理边界

> 形态决策见 [ADR-0004](../../../docs/adr/0004-l06-mcp-optional-thin-adapter.md)：自用定位下，L06 是**工具治理边界 + 复用机制**，不是开放平台底座。完整 MCP Server 为**可选**形态，默认用薄适配器。

## 职责
把外部工具、数据源、第三方系统适配成 L02 Agent 可调用的标准能力，并作为**所有出站调用的统一治理边界**（白名单 / 审计 / 凭证，对应 CONSTRAINTS 第 164/175 行、P-3）。

L06 对外只暴露一个**统一工具注册表接口**，L02 Agent 只认这个接口，不关心底层是 MCP 还是普通函数。

## 实现形态（ADR-0004）

| 场景 | 默认形态 | 何时升级为完整 MCP Server |
|---|---|---|
| 自研工具 / 自有数据源（Syslog / DB / 内部 API） | **薄适配器**（Python 函数 / CLI 封装），挂注册表接口后 | 确有远程部署 / 授权握手 / MCP resources 需求时 |
| 厂商**已发布官方 MCP Server**（如 CrowdStrike） | **直接消费**现成 MCP | —（本就是 MCP） |
| 未来若改商业化、需被项目外部消费 | 完整 MCP Server | 需先有新 ADR 推翻 ADR-0003 自用定位 |

**上下文策略**：Agent 调"少量代码 API"，不把几十个工具 schema 全塌进上下文（code execution over MCP），服务抑制幻觉铁律 C-24/26/27。

## 子组件
> 下列分类描述的是**接哪些系统**，与底层是 MCP 还是薄适配器无关——两种形态都挂在同一注册表接口后。

- **security_tools/** —— 安全工具适配
  - SIEM（Splunk / QRadar / 奇安信天眼）
  - EDR（CrowdStrike Falcon / 深信服 EDR）
  - NDR / XDR
  - 漏洞扫描（Nessus / 绿盟 RSAS）
  - 蜜罐 / WAF / IDS
- **data_sources/** —— 数据源适配（DB / OSS / Kafka / ES）
  - ⭐ **elasticsearch/** —— **P0/P1 优先**：用户日志主存在 ES 8.x，就地查询、不抽取入库（见 [ADR-0009](../../../docs/adr/0009-logs-in-elasticsearch-query-in-place.md)）。薄适配器 + `elasticsearch-py` 8.x，调查/富化的主取数通道。
- **protocols/** —— 通讯协议 MCP（SSH / WinRM / SNMP / Syslog）
- **vendors/** —— 各厂商专有 API MCP
- **aiops/** —— AIOps 系列 MCP（Prometheus / Zabbix / Grafana）
- **custom/** —— 自定义 Agent 功能 MCP

## 业界对标
- Microsoft Security Copilot 的 300+ 连接器生态
- Charlotte Agentic SOAR 的第三方 Agent 编排
- Anthropic MCP 官方协议规范

## 当前状态
🟢 部分 —— 已实现 ToolRegistry + ES 薄适配器（log_source）+ Notifier（出站经 L12 SSRF 白名单，C-22）+ 适配器 CRUD/启停/连通测试。六大类其余按需接入。

## 为什么不再把 L06 当"平台底座"（ADR-0004）
旧版这里写的是"Agent Marketplace + MCP 连接器生态 / 决定平台能不能开放"。但 [ADR-0003](../../../docs/adr/0003-self-use-positioning.md) 把项目定位为**自建自用**后，消费方只有一个（自己的 L02 Agent），"写一次任何客户端都能用"的标准化收益基本蒸发，却照付上下文膨胀 + 完整 Server 的开发成本。

因此 [ADR-0004](../../../docs/adr/0004-l06-mcp-optional-thin-adapter.md) 把 L06 的价值重新定位为：**工具治理边界（白名单/审计/凭证）+ 复用机制（统一注册表接口）**，而非开放生态。厂商现成 MCP 直接消费，自研工具用薄适配器。

# ADR-0004 · L06 执行形态：自用定位下 MCP 降级为可选，默认薄适配器 + code execution

- 状态：Accepted
- 日期：2026-06-03
- 决策者：muzi
- 关联修订：细化 [ADR-0003](0003-self-use-positioning.md) 的"MCP-first（L06）保留"一条

## 背景

L06 现有设计（见 `src/aisecops/L06_mcp_servers/README.md`）把**所有**外部工具/数据源/协议都要求适配成完整 MCP Server，并在多处被固化：

- L06 README："基于 MCP 把外部工具适配成标准能力，是平台扩展生态的关键层"
- 技术设计 P-3：**"外部工具必经 L06 MCP"**
- CONSTRAINTS 第 98 行：跨层直连的例外只能是"L05 Gateway / L06 MCP / L12 横切支撑"
- L06 README 第 27-28 行的理由：**"决定平台能不能开放——是单体应用还是平台底座 / Agent Marketplace + MCP 连接器生态"**

这套"MCP-first"的核心论证，前提是**存在多个、未知的工具消费方**（开放生态 / 连接器市场 / 第三方 Agent 编排）。MCP 最硬的价值就是"写一次，任何 MCP 客户端都能用"的标准化。

但有两个新情况让这个前提失效：

1. **定位变了（ADR-0003）**：项目已明确为"自建自用内部工具"，**不做商业化 / 多租户 / 平台 / marketplace**。L06 的消费方实际上只有**一个**：自己的 L02 Agent。"写一次任何客户端都能用"的标准化收益基本蒸发，但写完整 MCP Server 的成本照付。
2. **业界在"去 MCP 重量化"（2025-2026）**：
   - MCP Server 启动会把**全部 tool schema 灌进上下文**。L06 列了 SIEM/EDR/NDR/漏扫/蜜罐/DB/Kafka/SSH/SNMP 等几十个工具，光 schema 就吃掉大量 token，工具结果回传再来一轮——直接污染上下文。
   - Anthropic 官方《Code execution with MCP》(2025-11) 承认该问题，给出的解法是 **"让 Agent 写代码去调工具，而不是把每个工具都暴露成 schema"**，实测省 ~98% token。业界落点是 **"code execution over MCP"**，而非"CLI 取代 MCP"。

这与本项目抑制幻觉铁律（C-24/26/27，要求干净上下文）方向一致：上下文越干净，幻觉越少。

## 决策

**保留 L06 这一层及其治理职责，但把"实现形态"放轻。** 具体分三条：

### 1. L06 = 契约 + 治理边界（保留，不动）

- "外部工具必经 L06"（P-3）的**治理语义保留**：所有出站调用仍必须经 L06 统一过白名单（CONSTRAINTS 第 164 行）、审计（第 175 行）、凭证管理（L12）。
- L06 对外暴露一个**统一的工具注册表接口**（registry），L02 Agent 只认这个接口，不关心底层是 MCP 还是函数。

### 2. 底层执行形态：默认"薄适配器"，完整 MCP Server 降为可选

| 场景 | 默认形态 | 何时升级为完整 MCP Server |
|---|---|---|
| 自研工具 / 自有数据源（Syslog / DB / 内部 API） | **薄适配器**（Python 函数 / CLI 封装），挂在 L06 注册表接口后 | 确有远程部署、授权握手、MCP resources/prompts 需求时 |
| 厂商**已发布官方 MCP Server**（如 CrowdStrike 等） | **直接消费**现成 MCP | —（本就是 MCP） |
| 需要被项目外部消费（未来若改商业化） | 完整 MCP Server | 定位若变回平台化（需新 ADR 推翻 ADR-0003） |

### 3. 上下文策略：采用 code-execution 模式

- L02 Agent 调用工具时，调"少量代码 API / CLI"，**不把几十个工具 schema 全塌进上下文**。
- 直接服务 C-24/26/27（干净上下文 → 抑制幻觉）。

### 对既有约束的影响

- **P-3 不变**：仍"外部工具必经 L06"，只是 L06 内部实现形态放宽。
- **CONSTRAINTS 第 98 行不变**：L06 仍是跨层直连的合法例外。
- **L06 README 需修订**：删/改第 27-28 行"平台底座 / Agent Marketplace"理由（在 ADR-0003 自用定位下已失效），改为"自用单客户端下，L06 是工具治理边界 + 复用机制"。
- **ADR-0003 第 44 行细化**：原"MCP-first（L06）保留"→ "L06 工具复用 + 治理机制保留，完整 MCP Server 降为可选"。注册表接口保证了"工具复用机制"这一 ADR-0003 想要的收益仍然成立。

### 落到 P0（Syslog demo）的具体做法

**不**用 `/add-mcp` 生成完整 MCP Server。先写 `L06/data_sources/syslog_adapter.py`（普通 Python 函数 / CLI 封装），挂在 L06 注册表接口后。接口长得像 MCP，实现是函数；将来真要变 MCP，**换实现不换接口**。

## 后果

**正面**：
- P0 落地更快——一个包 SDK 的函数比一个完整 MCP Server 快几倍。
- 上下文显著变干净，直接强化抑制幻觉铁律。
- 自用单客户端不再为"开放生态"付不必要的成本。
- 仍保留"换实现不换接口"的升级路径，未来要 MCP 化成本可控。

**负面**：
- 失去"任何 MCP 客户端即插即用"的标准化（但自用场景本就用不到）。
- 团队若已熟悉 MCP 范式，需理解"注册表接口 + 薄适配器"这层抽象。
- 需要回改 L06 README / P-3 表述 / `/add-mcp` 脚手架的默认产物（让它能生成薄适配器，而非只生成完整 Server）。

**风险**：
- 薄适配器若不严格走 L06 注册表，可能绕过白名单/审计 → 通过"L02 只认注册表接口、禁止直连"约束缓解（同 CONSTRAINTS 第 98 行精神）。
- 未来若商业化，需要把关键工具补成完整 MCP Server → 因接口不变，属增量改造，成本可控。

## 备选方案

### 备选 1：维持现状（全部完整 MCP Server）
- 拒绝理由：自用单客户端下，标准化收益蒸发，却照付上下文膨胀 + 开发成本，与 ADR-0003 务实精神冲突。

### 备选 2：彻底改 CLI / 抛弃 MCP（"外部工具必经 CLI"）
- 拒绝理由：丢掉 L06 的治理边界（白名单/审计/凭证）会违反 CONSTRAINTS 第 164/175 行；且厂商现成 MCP Server 没法直接消费。业界共识也是"code execution over MCP"而非"CLI 取代 MCP"。

### 备选 3：先不改，记进记忆等想清楚
- 拒绝理由：P-3 / L06 README / 技术设计已把"必经完整 MCP"写死，不落 ADR 下次会按旧理由打回；P0 马上要写 Syslog，需要现在就定形态。

## 后续行动

- [x] muzi 确认，状态改 Accepted
- [x] 修订 `src/aisecops/L06_mcp_servers/README.md`（删平台底座理由，加薄适配器 + 注册表接口说明）
- [x] 修订 `docs/specs/technical-design.md` P-3 表述（"必经 L06"保留，澄清内部形态可为薄适配器）
- [x] 调整 `/add-mcp` 脚手架：默认产出薄适配器，`--full` 才产完整 MCP Server
- [x] ADR-0003 第 44 行加一句指向本 ADR 的细化说明
- [x] 更新 ADR 索引（README.md）+ CLAUDE.md 关联

## 关联

- [ADR-0001 12 层架构基线](0001-architecture-baseline.md)
- [ADR-0003 自建自用定位](0003-self-use-positioning.md)（本 ADR 细化其"MCP-first"一条）
- [L06 README](../../src/aisecops/L06_mcp_servers/README.md)
- [技术设计 §3.3 MCP 生态](../specs/technical-design.md)
- CONSTRAINTS 第 98 / 164 / 175 行；P-3
- 参考：Anthropic《Code execution with MCP: building more efficient agents》(2025-11)

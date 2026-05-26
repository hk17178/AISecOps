# ADR-0001 · 采用 12 层架构作为 AISecOps 基线

- 状态：Accepted
- 日期：2026-05-26
- 决策者：muzi

## 背景

项目立项时面临三个具体问题：

1. **国内类似定位的开源项目（如 qinshihu/itops-agent-platform）距离业界成熟 AISecOps 差距巨大**：
   - 仅 11 stars，单作者
   - 名字叫"ITOps"——SEC 维度为零
   - 9 个扁平 Agent + 纯 LLM + SQLite，对照 Charlotte / QAX-GPT 等成熟度约 5-10%
2. **业界 2026 已有清晰的 AISecOps 公约数**：
   - 5+1 Multi-Agent 角色（Triage/Investigation/Enrichment/Verification/Reporting + Orchestrator）
   - LLM + DSLM + ML + 统计 + 静态分析 多模型混合
   - 250+ 连接器 / MCP 生态
   - SIEM / EDR / NDR / TI 数据源
   - HITL + Shadow AI 治理
3. **用户已有一张 12 层架构图（PNG）**：分层覆盖了 AI Agent、平台管控、AI 资产、Gateway、MCP、业务能力、分析引擎、数据中台、数据采集、被管对象、核心支撑等 12 个维度，骨架完整度对照业界基线 80-85%。

## 决策

采用现有的 12 层架构图作为项目基线，**目录与代码组织一一对应到 L01 ~ L12**：

```
src/aisecops/L01_human_interface/
src/aisecops/L02_agents/
src/aisecops/L03_ai_assets_rag/
src/aisecops/L04_ai_assets_models/
src/aisecops/L05_gateway/
src/aisecops/L06_mcp_servers/
src/aisecops/L07_secops_capabilities/
src/aisecops/L08_analytics_engines/
src/aisecops/L09_data_platform/
src/aisecops/L10_data_collection/
src/aisecops/L11_target_estate/
src/aisecops/L12_core_support/
```

视觉权威是 `docs/architecture.png`，**冲突以图为准**。

## 后果

**正面**：
- 一开始就对齐业界基线，避免 itops-agent-platform 的"AIOps 套壳"陷阱
- 12 层 → 12 个清晰职责，新功能落点决策有依据
- 后续接入 MCP 生态、引入 DSLM 都有现成位置
- 文档与代码可视觉直接对应

**负面**：
- 12 层骨架前期看起来"过于豪华"——很多层短期内不会动
- Python import 路径较长（`from aisecops.L05_gateway.llm_gateway import ...`）
- 学习成本较高（新人需要先理解 12 层）

**风险**：
- 如果某些层永远没人填，会变成"僵尸层"——用 `/verify-layer` 周期性体检
- 跨层调用边界容易破坏——引入 [[layer-architect]] subagent 守门

## 备选方案

### 备选 1：扁平架构（如 itops-agent-platform 风格）
- 不分层，所有代码在 `src/` 下平铺
- 拒绝理由：业界反模式典型，已有失败案例

### 备选 2：按业务域拆（DDD 风格）
- 例如 `alerts/` `investigation/` `soar/` `data/` 各自独立
- 拒绝理由：丢失了"AI 资产层 / Gateway / MCP / 分析引擎"等横切关注点的清晰位置

### 备选 3：按部署单元拆（micro-service 风格）
- 每个 L 层是一个独立服务
- 推迟理由：现阶段是单仓库骨架，过早微服务化是 over-engineering。**P3 之后可以演进**——架构图本身支持。

## 关联

- [README.md](../../README.md)
- [CONSTRAINTS.md](../../CONSTRAINTS.md)
- [PRINCIPLES.md](../../PRINCIPLES.md)
- [架构图](../architecture.png)

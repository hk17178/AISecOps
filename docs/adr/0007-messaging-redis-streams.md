# ADR-0007 · 数据中间件起步用 Redis Streams（不上 Kafka）

- 状态：Accepted
- 日期：2026-06-04
- 决策者：muzi
- 来源：正式化 [technical-design §3.4](../specs/technical-design.md) + [ADR-0004/O2 精简栈]

## 背景

平台需要消息中间件做 Agent 间通信与告警流（alerts.raw、analyst.feedback 等）。候选：Redis Streams / Kafka。同时（O2 决策）PoC 数据层已砍到 PG + Redis 两个有状态服务。

## 决策

**消息中间件起步 = Redis Streams**（已有的 Redis 实例复用，不单独上 Kafka）。

- 自用 EPS 目标 1-5K（实际可能 100-500），Redis Streams 足够。
- 复用 Redis（同时做缓存/队列），少一个有状态服务，贴合"单人可维护/零运维"。
- 接口面向"消息总线"抽象，吞吐撑不住（> 1K EPS 持续）时可替换为 Kafka，不改业务。

向量与时序起步也并入 PG（pgvector + JSONB/分区表），见 [technical-design §3.4](../specs/technical-design.md)。

## 后果

**正面**：中间件最少、运维最轻、起步快。
**负面**：Redis Streams 的持久化/回溯能力弱于 Kafka（自用可接受）。
**风险**：数据量超预期 → 按 O2 升级表换 Kafka，属增量。

## 关联

- [technical-design §3.4](../specs/technical-design.md) · [ADR-0004 L06 形态](0004-l06-mcp-optional-thin-adapter.md)（O2 精简栈）

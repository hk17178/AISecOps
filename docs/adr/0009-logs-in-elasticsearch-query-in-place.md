# ADR-0009 · 日志主存用现有 Elasticsearch 8.x，就地查询（平台不自存原始日志）

- 状态：Accepted
- 日期：2026-06-04
- 决策者：muzi
- 关联修订：technical-design §3.4 数据层 / §5 数据流；细化 [ADR-0004](0004-l06-mcp-optional-thin-adapter.md)（L06 薄适配器）；部分回答 PRD §9 #2（数据源）

## 背景

确认了关键环境事实：**用户绝大部分日志已存在 Elasticsearch 8.x 中。**

而原设计（technical-design §3.4 + §5.1 数据流）假设平台**自建日志存储**：日志先入 PG（JSONB），撑不住再上 ClickHouse；并把 OpenSearch/ClickHouse 列为"起步不上、撑不住再加"。

这套假设在"日志已在 ES"的现实下是**重复造轮子**：把已经在 ES 里的日志再抽一份进我们自己的库，既增加存储与同步成本，又违背自用"零运维 / 够用就行"。

## 决策

**ES 8.x 是平台的主日志源；采用就地查询（query-in-place），平台不自存原始日志。**

1. **取数方式**：要日志/做调查取证时，**去 ES 查**，不抽取、不囤原始日志副本。
2. **接入形态**：在 L06 加 **`data_sources/elasticsearch` 薄适配器**（ADR-0004），封装 ES 查询；L02/L07/L08 经统一注册表接口调用，走 L12 凭证 + 白名单/审计（CONSTRAINTS C-9/164/175）。
3. **客户端库**：`elasticsearch-py` **8.x**（与服务端大版本对齐）。**注意：不是 OpenSearch**，不能用 `opensearch-py`，也别用版本不匹配的 7.x 客户端。
4. **平台自存什么**：只存**衍生/轻量数据**——告警、研判结论、审计链、Agent Memory、向量——用 PG（pgvector）。**原始日志不进我们的库**。
5. **ClickHouse 退出 V1 计划**：原"日志撑不住上 ClickHouse"取消。只有将来确需**自有大规模衍生分析数据**（而非原始日志）时再按需评估，另写 ADR。
6. **实时告警仍走 webhook**：SIEM/EDR 的实时告警经 webhook 进 L10（实时触发分诊）；ES 主要服务**历史日志检索与调查取证富化**。二者互补。

ES 适配器因此成为 **L06 的 P0/P1 连接器**（与 Syslog/通知并列），是调查/富化场景的主取数通道。

## 后果

**正面**：
- 省掉自建日志存储与 ETL 入库一整块工程，最贴自用"零运维"。
- 不重复存数据，无同步一致性问题。
- 复用用户既有 ES 投资，落地快。

**负面 / 风险**：
- 平台能力依赖 ES 可用性与查询性能 → 适配器加超时/限流/降级；高频查询加缓存（Redis）。
- 跨源关联（ES 日志 + 我方告警）需在查询层拼装，不在同一库 join → L08 关联逻辑面向"多源查询"设计。
- 需要 ES 只读账号/凭证 → 走 L12 secrets，最小权限。
- 大范围历史检索可能慢/重 → 调查场景按时间窗 + 字段裁剪查询，不全量拉。

## 备选方案

- **抽取入库（ES → ClickHouse）**：拒绝。重复存储、要维护同步管道，自用无收益。
- **自建日志存储（不接 ES）**：拒绝。和现实脱节，等于让用户日志搬家。

## 关联

- [ADR-0004 L06 薄适配器](0004-l06-mcp-optional-thin-adapter.md) · [ADR-0008 跨层 DAG](0008-cross-layer-dependency-dag.md)
- [technical-design §3.4 / §5](../specs/technical-design.md) · PRD §9 #2
- [L06 README](../../src/aisecops/L06_mcp_servers/README.md)

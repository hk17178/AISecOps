# L09 · 数据中台 (Data Lake / Pipeline)

## 职责
企业级数据归集与处理底座。把 L10 采集来的异构 telemetry 归一化、富化、加工成 L08 分析引擎和 L03 RAG 可用的资产。

## 子组件
- **ingest/** —— 数据采集（实时 / 批量）
- **transit/** —— 数据中转池（Kafka / Pulsar）
- **etl/** —— ETL 工程
- **feature_store/** —— 特征工程与特征存储
- **data_lake/** —— 数据湖（原始 / 处理 / 应用三层）
- **eda/** —— 数据探索分析

## 业界对标
- Splunk / Datadog 数据 ingest pipeline
- Google SecOps 的 ingestion layer
- 阿里云日志服务 SLS

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

## 为什么 SQLite 不行
itops-agent-platform 用 SQLite 单库——这是玩具级。安全 telemetry 是 TB/PB 级，必须企业级数据中台。

# L12 · 核心支撑能力 (Core Supporting Capabilities)

## 职责
平台横切的基础设施能力，被其他所有层依赖。

## 子组件
- **asset_identification/** —— 资产识别与 CMDB
- **scheduling/** —— 调度集群（任务调度 / 资源调度 / Agent 调度）
- **observability/** —— 平台自身可观测（指标 / 日志 / 追踪）
- **secrets/** —— 凭证管理（Vault 集成）

## 业界对标
- HashiCorp Vault
- Kubernetes 调度
- 各家 CMDB 系统

## 当前状态
🟢 部分 —— 已实现横切核心：secrets（Fernet 加密 + scrypt 口令哈希 + 生产 fail-closed）/ config（DB 覆盖 .env）/ db（PG 连接池）/ audit（哈希链，可落 PG）/ net_guard（出域判定 + SSRF 防护）/ observability（OTel）。scheduling 待补。

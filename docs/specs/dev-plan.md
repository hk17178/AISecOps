# 开发计划 · AISECOPS

- 版本：v0.1
- 状态：Draft（骨架阶段）
- 日期：2026-05-26
- 作者：muzi
- 关联：[PRD](PRD.md) · [技术设计](technical-design.md) · [V2 架构](../architecture-v2.md)

---

## 1. 总览

### 1.1 节奏
- **Sprint = 2 周**
- **季度评审 + Roadmap 调整**
- 单人 / 小团队节奏（用户 + AI 辅助），不强排"人时"

### 1.2 阶段划分

| 阶段 | 时间 | 目标 | 交付级别 |
|---|---|---|---|
| **P0** | 2026 Q2-Q3 | 最小可跑 demo | Internal Demo |
| **P1** | 2026 Q3-Q4 | 安全闭环 | Alpha（内部试用） |
| **P2** | 2026 Q4 - 2027 Q1 | 平台化 | Beta（PoC 客户） |
| **P3** | 2027 Q1-Q2 | V1.0 发布 | GA |
| **P4+** | 2027 Q2+ | 商业化 / 国际化 | 商业版 |

### 1.3 整体里程碑

```
2026-Q2  ─┬─ M0: 骨架完成（已达成 2026-05-26）
2026-Q3  ─┼─ M1: P0 最小可跑（L05 + L02 + 1 MCP + L07.triage）
         └─ M2: P1 安全闭环（L08 攻击图 + L09 ETL + L10 采集）
2026-Q4  ─┬─ M3: P2 平台化（DSLM + 多 MCP + 多租户 + AI 合规）
         └─ M4: Alpha 内部试用
2027-Q1  ─┬─ M5: Beta PoC 客户
         └─ M6: V1.0 GA
```

---

## 2. P0 详细计划（最小可跑 Demo）

**目标**：单条告警端到端走通分诊流程。

### Sprint 1：基础设施（2 周）
- **S1.1** 选型决策落地：写 ADR-0003 ~ ADR-0006
- **S1.2** Python 环境：pyproject.toml 完整、uv 切换、ruff/mypy 配置
- **S1.3** 容器化：Dockerfile + docker-compose.yml 基础（Postgres/Kafka/Redis/MinIO）
- **S1.4** CI：GitHub Actions（lint + type + test 三步）
- **S1.5** 可观测基础：OpenTelemetry trace 接入

**DoD**：
- `make dev` 可启动完整本地环境
- `make test` 全绿
- CI 在 PR 上自动跑

### Sprint 2：L05 LLM Gateway（2 周）
- **S2.1** Gateway 基础架构 + 多 provider 路由
- **S2.2** 豆包 + Claude provider 实现
- **S2.3** Metadata 记录（C-33）
- **S2.4** Stub mode（C-18）
- **S2.5** 出域开关 + 脱敏（C-32）
- **S2.6** 降级链（C-34）
- **S2.7** 单元测试 ≥ 80% 覆盖
- **S2.8** 集成测试：调用国产 LLM 真实回路

**DoD**：
- 业务层一行 `await gateway.call(...)` 完成调用
- Stub mode 下 pytest 不烧 token
- 出域开关默认关闭，验证生效

### Sprint 3：L02 Orchestrator + L02 Triage Agent（2 周）
- **S3.1** Agent 基类 + Orchestrator 框架
- **S3.2** Triage Agent 实现（Pydantic Output schema）
- **S3.3** abstain 机制（C-26）
- **S3.4** 双模型 cross-check 框架（C-27，暂不强制启用）
- **S3.5** Memory Store 基础（先用 Postgres）
- **S3.6** 审计日志 append-only（C-23）

**DoD**：
- 给 Orchestrator 一条告警 → 路由到 Triage → 返回结构化结果
- 输出含 verdict / confidence / evidence / abstain 可选
- 审计日志可查

### Sprint 4：L06 第一个 MCP Server + L07 alert_triage（2 周）
- **S4.1** MCP 脚手架（`/add-mcp` 命令实现）
- **S4.2** Syslog MCP（data_sources 类）
- **S4.3** L07 alert_triage 业务能力（编排 Orchestrator + Triage Agent + Syslog MCP）
- **S4.4** L01 最小 UI：告警列表 + 分诊结果（React + shadcn/ui）
- **S4.5** 端到端 demo：从 Syslog 摄入到 UI 展示

**DoD**：
- 一条 Syslog 告警 → 5 分钟内 UI 出分诊结果
- 含证据链 + 置信度 + abstain 状态
- eval set ≥ 30 条样本

---

## 3. P1 详细计划（安全闭环）

**目标**：补齐安全分析半边，能做攻击链还原 + 简单 SOAR。

### Sprint 5-6：L08 攻击图引擎（4 周）
- 图数据结构 + Neo4j 集成
- attack_graph 基础算法（基于 ATT&CK）
- kill_chain 还原
- ioc_correlation 算法

### Sprint 7：L09 ETL 最小管道（2 周）
- Kafka → Flink → ClickHouse 基础流
- 告警归一化（多源 → 统一 schema）

### Sprint 8：L10 多源采集（2 周）
- Syslog / 文件 / Webhook 三种采集模式
- 主机 Agent 暂用 Filebeat

### Sprint 9：L07 investigation 业务能力（2 周）
- Investigation Agent（NL 取证）
- 调用 L08 攻击图 + L06 多 MCP
- 时间线 + 攻击链可视化（前端）

### Sprint 10：SOAR Playbook 最小版（2 周）
- L02 SOAR Playbook 引擎骨架
- HITL Channel 实现
- 1 个剧本：封 IP（高风险动作 + 双模型 + HITL）

---

## 4. P2 详细计划（平台化）

**目标**：从单租户 demo 变成可对外的 Beta。

### Sprint 11-12：L04 DSLM 飞轮（4 周）
- log_classifier DSLM 训练管道
- 反馈飞轮：L01 → L02 Tuning → L04 训练
- Shadow Mode 评估（P-11）

### Sprint 13-14：多租户 + IAM（4 周）
- 数据行级隔离
- 完整 IAM（用户 / 角色 / 资源权限）
- 客户管理后台

### Sprint 15：L11 AI 合规对象（2 周）
- AI 模型 CMDB
- Shadow AI 监管基础

### Sprint 16：L01 完整 UI（2 周）
- 4 个面板：告警 / 工单 / 报表 / Chat
- 仪表盘 + KPI（MTTD/MTTR/误报率）

### Sprint 17：MCP 生态扩充（2 周）
- 目标 ≥ 20 个 MCP
- 优先：SIEM/EDR/防火墙/WAF/TI/CMDB

### Sprint 18：威胁建模 + 安全测试（2 周）
- STRIDE 威胁建模
- 安全红队 PoC
- 渗透测试

---

## 5. P3 详细计划（V1.0 GA）

### Sprint 19-22：稳定性 + 性能（8 周）
- 性能压测（达成 PRD §5.1 性能指标）
- HA 设计 + 实现
- 客户文档完整
- 部署自动化

### Sprint 23：等保 2.0 三级合规改造（2 周）
- 安全控制项对照
- 审计 / 日志 / 加密 / 访问控制 完善

### Sprint 24：GA Release（2 周）
- 文档冻结
- 客户培训材料
- License 系统

---

## 6. 关键路径（Critical Path）

```
S1 基础设施
  ↓
S2 L05 LLM Gateway ───────────┐
  ↓                            ↓
S3 L02 Orchestrator ──── S4 L07 alert_triage (P0 完成)
  ↓                            ↓
S5-6 L08 攻击图               S7 L09 ETL
  ↓                            ↓
S9 L07 investigation ←──── S8 L10 采集
  ↓
S10 SOAR (P1 完成)
  ↓
S11-12 DSLM 飞轮
  ↓
S13-14 多租户 ──── S15 AI 合规 ──── S16 UI ──── S17 MCP
  ↓
S18 威胁建模 (P2 完成)
  ↓
S19-24 P3 GA
```

**最长链**：S1 → S2 → S3 → S4 → S5-6 → S9 → S10 → S11-12 → S13-14 → S18 → S19-24 ≈ **42 周**

---

## 7. 依赖与风险

### 7.1 关键依赖
| 依赖 | 风险等级 | 缓解策略 |
|---|---|---|
| 国产 LLM API（豆包等）稳定性 | 🟡 中 | 多 provider 路由 + 降级链（C-34） |
| Anthropic MCP SDK 演进 | 🟡 中 | 跟踪官方版本 + 自研抽象层 |
| 开源 DSLM 基础模型可用性 | 🟢 低 | Qwen / DeepSeek 都已开源 |
| 客户 PoC 资源 | 🔴 高 | P2 阶段需主动找 1-2 家本地大客户 |
| 团队规模 | 🔴 高 | 单人 + AI 辅助节奏，关键模块外包评估 |

### 7.2 主要风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| LLM 幻觉导致客户事故 | 中 | 高 | CONSTRAINTS C-24~C-27 强约束 + eval set + HITL |
| 业界竞品（如 QAX-GPT）快速领先 | 高 | 中 | 差异化：MCP-first + 可重现 + 双部署模式 |
| 数据中台选型错误 | 中 | 高 | P0 完成 ADR-0005 PoC 后再大规模建设 |
| 团队人手不足 | 高 | 高 | Scope 控制；P0/P1 是单人可完成的 |
| 客户合规要求超预期 | 中 | 中 | 等保 2.0 三级提前布局 |
| 政策法规变化 | 低 | 高 | 关注网信办 / 工信部 AI 安全相关法规 |

---

## 8. Definition of Done（DoD）通用

每个 Sprint 的交付物必须满足：
- [ ] 功能实现 + 单元测试 ≥ 80% 覆盖
- [ ] 集成测试 1+ 个 happy path
- [ ] 文档：模块 README + 必要时 ADR
- [ ] CI 全绿（lint + type + test）
- [ ] eval set（LLM 业务必需，C-31）
- [ ] 安全自查：无凭证硬编码 / 输入校验 / 出域开关
- [ ] 中文注释 + docstring（C-28）
- [ ] PR review by AI subagent（security-analyst / layer-architect）
- [ ] 演示给用户看（关键 Sprint）

---

## 9. 工具与流程

### 9.1 项目管理
- GitHub Issues + Milestones（按 Sprint）
- Project Board（Kanban）
- 每 Sprint 评审：Demo + Retro

### 9.2 文档维护节奏
- PRD / 技术设计：每季度 review，必要时 v0.X → v1.X
- ADR：决策当时立刻写
- README：随代码变化
- CONSTRAINTS / PRINCIPLES：极少改，改必有 BREAKING ADR

### 9.3 模型 / Prompt 版本管理
- Prompt 走 git（`L02_agents/*/prompts/`）
- 模型版本走 ADR（不入 git）
- DSLM 训练样本 + 模型工件走对象存储（C-10 不入库）

---

## 10. 团队与角色（当前 + 演进）

### 10.1 当前（2026-05-26）
- 用户：技术架构 + 产品 + 开发
- AI（Claude）：辅助设计 + 编码 + review

### 10.2 P1 阶段建议引入
- 后端工程师 1 名（数据中台 + Flink）
- 前端工程师 1 名（L01 完整 UI）

### 10.3 P2 阶段建议引入
- 安全研究员 1 名（攻击图 + DSLM 训练数据）
- DevOps 1 名（K8s + 多租户运维）
- 销售 / PoC 工程师（找客户）

### 10.4 P3 GA 阶段
- 完整研发团队（10+ 人）
- 销售 + 售前 + 实施
- 客户成功

---

## 11. 与 PRD §10 待决策事项的关联

| PRD 待决策 | 何时决策 | 触发条件 |
|---|---|---|
| 客户首单 / SaaS 优先 | P1 结束前 | Alpha 内部跑通后 |
| 商业化时点 | P2 结束前 | Beta PoC 客户反馈后 |
| MSSP 通道 | P3 GA 后 | V1.0 稳定运行后 |
| 开源策略 | P2 阶段 | MCP 数量 ≥ 10 时 |
| 国际市场 | P4+ | 国内站稳后 |

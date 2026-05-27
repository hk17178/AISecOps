# 开发计划 · AISECOPS（自用版）

- 版本：v0.2（自用重写）
- 状态：Draft
- 日期：2026-05-26
- 作者：muzi
- 关联：[PRD](PRD.md) · [技术设计](technical-design.md) · [ADR-0003 自用定位](../adr/0003-self-use-positioning.md)

---

## 1. 总览

### 1.1 节奏
- **Sprint = 2 周**
- **单人 / 小团队节奏**（你 + AI 辅助 + 同事偶尔搭手）
- **能下班 / 能周末 / 兴趣驱动**

### 1.2 节奏期望
- **PoC**：3 个月内能跑通"一条告警进来到分诊结果出来"
- **同事可用**：4 个月内 1-2 个同事开始日常用
- **稳定运行**：6 个月内基本不出故障

### 1.3 整体里程碑

```
2026-Q2  ─┬─ M0: 骨架完成（✅ 2026-05-26 已达成）
         └─ M1: Sprint 1-2 基础设施 + LLM Gateway 跑通
2026-Q3  ─┬─ M2: Sprint 3-4 第一个 Agent + 一个 MCP + alert_triage 端到端
         └─ M3: Sprint 5-6 事件调查 + 通知 + 工单
2026-Q4  ─┬─ M4: Sprint 7-8 数据中台 + 报告 + Playbook
         └─ M5: 同事开始用
2027-Q1  ─── M6: 稳定运行 / 优化 / 看真实问题加 feature
```

### 1.4 阶段对比

| 阶段 | 之前商用版 | 自用版（现在） |
|---|---|---|
| 总长 | 42 周到 GA | **~16 周到"同事用起来"** |
| Sprint 数 | 24 | **6-8** |
| 团队 | 单 → 完整 10+ 人 | **你 + 同事偶尔** |

---

## 2. P0 阶段 · Sprint 1-4（最小可跑 + 告警分诊）

### Sprint 1：基础设施（2 周）

**目标**：把项目能跑、能 CI、能观测起来。

- **S1.1** 决策落地：写 ADR-0004 ~ ADR-0006（主语言 / Agent 编排 / 数据中间件）+ 5 条 PRD §9 待决策事项
- **S1.2** Python 环境：pyproject.toml + uv + ruff + mypy
- **S1.3** Docker：Dockerfile + docker-compose.yml（PG + ClickHouse + Redis + MinIO + Vault）
- **S1.4** CI：GitHub Actions（lint + type + test 三步）
- **S1.5** OpenTelemetry 可观测最小集成（trace + log + metric）
- **S1.6** 写 `docs/restart-guide.md` 第一版（未来重启自己用）

**DoD**：
- `make dev` 一键起本地环境
- `make test` 全绿
- CI 在 PR 触发
- 浏览器打开 Grafana 看到至少 1 个 metric

### Sprint 2：L05 LLM Gateway（2 周）

**目标**：所有 LLM 调用都走 Gateway，含成本控制。

- **S2.1** Gateway 基础架构 + 多 provider 路由
- **S2.2** 实现 1 个 SaaS provider（豆包 / 通义 / 智谱 任选）+ 1 个 OpenAI-compat provider（接 Ollama 本地）
- **S2.3** Metadata 记录（C-33）+ 成本统计（自用刚需）
- **S2.4** Stub mode（C-18）—— pytest 不烧 token
- **S2.5** 出域开关（默认关）+ 脱敏（C-32）
- **S2.6** 降级链（C-34）：备 model → stub → 报错
- **S2.7** ⭐ **月预算上限**告警（自用关键）
- **S2.8** 单测覆盖 ≥ 80%

**DoD**：
- 业务一行 `await gateway.call(...)` 完成
- Stub 模式 pytest 通过
- 月度成本仪表盘可见
- 出域开关验证生效

### Sprint 3：L02 Orchestrator + Triage Agent（2 周）

**目标**：第一个 Agent 跑起来。

- **S3.1** Agent 基类 + Orchestrator 框架（不引 LangGraph）
- **S3.2** Triage Agent 实现 + Pydantic schema 强约束
- **S3.3** abstain 机制（C-26）+ 置信度阈值
- **S3.4** 双模型 cross-check 框架（C-27，**初期不强制启用**，给 Playbook 用）
- **S3.5** Memory Store（PG 实现简版）
- **S3.6** 审计日志 append-only（C-23 + 哈希链）

**DoD**：
- 给 Orchestrator 一条 mock 告警 → 路由到 Triage → 返回结构化结果
- 输出含 verdict / confidence / evidence / abstain
- 审计日志可查询
- eval set ≥ 20 条样本

### Sprint 4：L06 MCP + L07 alert_triage 端到端（2 周）

**目标**：M2 完成 —— 真告警进来能分诊。

- **S4.1** MCP 脚手架（`/add-mcp` 落地）
- **S4.2** Syslog MCP（采集类）—— 接你们 Syslog 流
- **S4.3** 1 个数据源 MCP—— 接你们现用 SIEM/EDR 任选其一
- **S4.4** L07 alert_triage 业务（编排 Orchestrator + Triage + MCP）
- **S4.5** L01 最小 UI：告警列表 + 分诊结果（React + shadcn/ui，**别花俏**）

**DoD**：
- 一条真 Syslog 告警 → 5 分钟内 UI 出分诊结果
- 含证据链 + 置信度 + abstain 状态
- eval set ≥ 50 条样本
- **里程碑 M2 ✅**

---

## 3. P1 阶段 · Sprint 5-6（事件调查 + 通知工单）

### Sprint 5：L07 investigation + 通知（2 周）

- **S5.1** Investigation Agent（NL 取证）
- **S5.2** L01 Chat 面板（自然语言提问）
- **S5.3** L08 简单关联分析（不上图算法，先做时间线 + IoC 关联）
- **S5.4** L02 通知中枢（企微 / 钉钉 / 邮件 任选一种 + Webhook 通用）

**DoD**：
- Chat 面板能问"这次告警怎么回事"，10 秒内出时间线
- 通知能发到你的企微 / 钉钉

### Sprint 6：L02 工单 + HITL Channel（2 周）

- **S6.1** L02 工单引擎（人工流转）
- **S6.2** HITL Channel 实现（横切层）
- **S6.3** L01 工单 UI + HITL 审批队列
- **S6.4** 3 角色 RBAC 实现

**DoD**：
- 告警自动开工单
- 高风险动作必经 HITL（你或同事审批）
- 3 角色权限隔离生效
- **里程碑 M3 ✅**

---

## 4. P2 阶段 · Sprint 7-8（报告 + Playbook + 数据中台）

### Sprint 7：L07 报告 + L09 数据中台（2 周）

- **S7.1** Reporter Agent + 自动日报 / 周报模板
- **S7.2** 报告导出（Markdown / DOCX）
- **S7.3** L09 ETL 简版（归一化 + 富化）
- **S7.4** 数据保留策略（30 天热 / 历史归档 MinIO）

**DoD**：
- 早上看到自动生成的昨日安全简报
- 数据 30 天可查

### Sprint 8：SOAR Playbook + 上线（2 周）

- **S8.1** L02 SOAR Playbook 引擎骨架
- **S8.2** 1 个剧本：封 IP（高风险，必经双模型 + HITL）
- **S8.3** 1 个剧本：禁用账号（同上）
- **S8.4** 演练 + 文档
- **S8.5** `docs/restart-guide.md` 完整化
- **S8.6** 上线（你和同事正式开始用）

**DoD**：
- 同事至少 1 人能独立完成"看告警 → 调查 → 审批 → 处置"全流程
- 2 个剧本可用
- **里程碑 M4 / M5 ✅**

---

## 5. P3+ 阶段（视实际需求）

> **不预排** —— 上线后看真实问题再决定。

### 候选 backlog（按需选）
- 攻击图 / Kill Chain 还原（如调查需求强）
- 更多 MCP 接入（如新数据源出现）
- 多团队 / 部门隔离（如公司其他部门想用）
- DSLM 训练（**前提**：5000+ 标注样本）
- 移动端只读
- 性能优化（如 EPS 撑不住）
- 国产化迁移（如有信创要求）

### 商业化（未来真要做时）
按 [ADR-0003 §7](../adr/0003-self-use-positioning.md) 增量：
- 多租户 / 双模式 / 合规对照
- 预计 3-6 个月

---

## 6. 关键路径

```
S1 基础设施
  ↓
S2 L05 LLM Gateway ────────────┐
  ↓                             ↓
S3 L02 Orchestrator + Triage ── S4 L06 MCP + alert_triage (M2 P0 完成)
                                ↓
                          S5 调查 + 通知
                                ↓
                          S6 工单 + HITL (M3 P1 完成)
                                ↓
                          S7 报告 + 数据中台
                                ↓
                          S8 Playbook + 上线 (M4/M5 P2 完成)
```

**最长链：8 Sprint = 16 周 ≈ 4 个月**。

---

## 7. 依赖与风险（自用版）

### 7.1 关键依赖

| 依赖 | 风险等级 | 缓解策略 |
|---|---|---|
| 国产 LLM API 稳定性 | 🟡 中 | 多 provider 路由 + stub 模式 |
| 你们公司 SIEM / EDR 现状 | 🟡 中 | Sprint 1 前调研清楚 |
| 同事配合度 | 🟡 中 | 早期参与 Demo，让他们能反馈 |
| 你的时间（兼职做） | 🔴 高 | scope 严格控制 / Sprint 间可调速 |

### 7.2 主要风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| LLM 幻觉处置错告警 | 高 | 高 | HITL 默认 + 双模型 + 引用必备 |
| 同事用不起来（嫌麻烦） | 高 | 中 | UI 简洁 + 减少配置 + 早期参与 |
| 你失去兴趣不维护 | 中 | 高 | 文档自洽 + restart-guide 让"重启"成本低 |
| 烧 LLM token 超预算 | 中 | 低 | C-33 metadata + 月预算告警 |
| 真实数据量比预想大 | 低 | 中 | Redis Streams 撑不住时换 Kafka |
| 真实数据量比预想小 | 高 | 低 | 不强行训 DSLM，飞轮 V3+ 再说 |

### 7.3 不再是风险（vs 商用版）

| 之前列的 | 为何现在不是风险 |
|---|---|
| 业界竞品快速领先 | 不竞 |
| 客户合规要求超预期 | 没客户 |
| 国家法规变化 | 自用关注但不卡 |
| 团队规模不足 | 接受单人慢节奏 |

---

## 8. DoD 通用清单

每个 Sprint 交付：
- [ ] 功能实现 + 单测 ≥ 70%（**自用降到 70%**）
- [ ] 集成测试 1+ 个 happy path
- [ ] 模块 README + 必要时 ADR
- [ ] CI 全绿
- [ ] eval set（LLM 业务必需，**自用 ≥ 20 条起步**）
- [ ] 安全自查：无凭证硬编码 / 输入校验 / 出域开关
- [ ] 中文 docstring（C-28）
- [ ] AI subagent review（security-analyst / layer-architect）
- [ ] Demo 给自己看（**没人验收时自己演一遍**）

---

## 9. 工具与流程

### 9.1 项目管理
- GitHub Issues + Milestones（按 Sprint）
- 不开 Project Board（自用没必要）
- 每 Sprint 末写一篇 retro（自用日记）

### 9.2 文档维护
- PRD / 技术设计：**每个里程碑 M 后 review**，不一定季度
- ADR：决策当时立刻写
- README：随代码变化
- restart-guide：每 Sprint 跟一次

### 9.3 Prompt 管理
- Prompt 走 git（`L02_agents/*/prompts/`）
- 一个 Prompt 一个文件，文件头加修改历史

---

## 10. 不做的事（再次明确）

- ❌ 客户 / 售前 / 实施 / 销售
- ❌ ISO 27001 / SOC2 / 等保认证
- ❌ 多租户 / 多团队
- ❌ HA / 灾备双活 / RTO/RPO 分级
- ❌ SLA / SLO 对外承诺
- ❌ License 系统 / 计费
- ❌ DSLM 训练（V3+ 再说）
- ❌ 移动端原生 App
- ❌ 国际化
- ❌ 性能极限优化（自用规模够用就行）

---

## 11. 自用项目的成功定义

```
不是 GA 上线
不是拿融资
不是赢竞品

是  —— 你和几个同事 6 个月后真在用
    —— 中间没有发生 AI 误判事故（C-8 HITL 起效）
    —— 你能把 12 层 / 34 铁律 / AI 工程方法讲得头头是道
    —— 文档 3 个月后自己看得懂
    —— 月成本 < ¥500，可承受
```

# CLAUDE.md · 项目对话上下文

> 本文件每次对话自动加载。**不要超过 200 行**——长了就改放 `.claude/context/`。

## 项目一句话

AISECOPS 是**自建自用**的 AI 驱动安全运营工具，给你/你们小公司/部门 10-100 人规模用，按 12 层架构组织，把"SEC"做成一等公民——业界对标 Charlotte/Copilot/QAX-GPT 但**不为了赢竞品**，是为了学透 AISecOps + 解决自己的 SOC 痛点。

**定位见 [ADR-0003 自用](docs/adr/0003-self-use-positioning.md)**。不做：商业化 / 多租户 / 合规认证 / 双部署模式。

## 当前阶段

🟢 **业务闭环成型中（分诊→降噪→关联→事件→调查→HITL）** —— L05 网关全做完 + 场景路由；前端 17 项 IA 实页 + Chat 挂件。72 测试，`make check` 全绿、CI 绿。`make serve`(:8000) + `cd frontend && npm run dev`(:5173)。
- ✅ 本地可跑可测：`make serve` 起服务，浏览器输入 prompt 调网关看响应+成本。无 key 走 stub；`.env` 配 `LLM_API_KEY` 即调真实 LLM。
- ✅ **L05 核心全做完**（S0–S10 + 治理三件套 S7–S9）。
- ✅ **Sprint 3 完成**：Orchestrator(路由) + Triage Agent（结构化研判 C-21 / 防注入 C-20 / abstain C-26 / cross-check C-27）+ Memory Store + 审计哈希链(C-23)。31 测试绿。
- ✅ **Sprint 4 后端端到端打通（M2 核心）**：L06 ES 适配器(薄适配器)+ L07 `alert_triage`。`POST /api/triage` 真实跑通 Orchestrator→Triage→ES 富化→研判（离线 stub 诚实 abstain，配真 LLM 出真研判）。39 源文件 / 37 测试绿。
- ✅ **L01 React 前端完整成型**（`frontend/`，暖纸主题）：登录页 + **17 项 IA 全部实页** + 路由保护 + 动效（翻牌/计数/入场/呼吸）。Triage 真调端到端、Settings 配置走 Web、工单 HITL 审批交互。typecheck+build 通过。
- ✅ **P1 告警库就位**：L09 AlertStore + L10 入库归一化 + `/api/ingest/alert` `/api/alerts` `/api/dashboard`。**仪表盘接真**（总数/真威胁/待研判/成本/最新告警，来自真 store）。Agent/MCP/成本 三页也是真后端。
- ✅ **HITL 工单系统**：真威胁研判→自动建单(C-8)→批准/驳回工作流（L02 tickets + `/api/tickets`），工单页接真后端、状态持久。
- ✅ **Investigation Agent**（L02 第二 Agent）：事件调查接真（ES 日志建时间线 + LLM 攻击链）。`/api/investigate`。
- ✅ **HITL 审批闭环**：工单批准/驳回**弹框填理由 → 写不可篡改审计链(C-23) → 审批记录可见**（Modal 组件 + `/api/audit`）。立起 CRUD+弹框+审计 标准模式。
- ✅ **PG 持久化地基**：仓储模式，告警/工单/路由/抑制规则/安全事件全可 PG（有 `DATABASE_URL` 走 PG，空/CI 走内存）。重启不丢。
- ✅ **L05 场景→模型路由**（§4.4）：`ScenarioRouter` 按场景分配大模型（分诊=快、调查/关联=强），`LLM_PROFILES` 配档位，`/api/routing` 增删改+审计，`模型&成本`页可编辑。
- ✅ **Chat 助手**改右下角常驻挂件（每页可用，经网关 `L01/chat` + C-20 沙箱）。
- ✅ **告警降噪**（§1.2，L08）：指纹去重+时间窗归并+抑制规则 CRUD，`告警降噪`页接真（降噪率/被抑制可回溯）。
- ✅ **关联分析**（§1.5，L08/L07）：并查集聚簇→LLM 跨告警攻击链(带引用 C-24)→人工确认建安全事件(PG)，`关联分析`页接真。
- ✅ **SOAR 处置**（§2.1，L02）：剧本 CRUD/启停 → 触发建 HITL 工单 → 批准执行 → 撤销，全程留痕，`SOAR 处置`页接真。
- ✅ **外发通知中枢**（§2.3，L02/L06）：渠道/外发规则/发送记录三件套(PG)，发送经 L06 适配器受出域开关约束(C-32，离线 stub 安全默认)，`外发·通知分发`页接真。
- ✅ **闭环已通**：采集→降噪→分诊→关联→事件→SOAR处置→外发通知→工单/HITL，审计贯穿。
- ⚠️ **仍欠账 CRUD**：Prompt/报表/CMDB/RBAC/Agent配置/系统配置持久化+密钥加密(§4.5)。按既有 CRUD+弹框+审计 模式补。
- 🔜 **下一步**：报表生成；CMDB/Prompt/Agent 配置 CRUD；L02 真 RBAC + 配置持久化。**日志接入(ES)留最后**。
- ✅ 环境齐全：Docker(Colima)+决策全定；后端 `make serve`(:8000)，前端 `cd frontend && npm run dev`(:5173)。

完整路线见 [dev-plan.md](docs/specs/dev-plan.md)。

## ⚠️ 五条必读铁律（违反就要回滚）

1. **SEC > OPS**（C-1）：L07 业务出口必须是安全场景（告警分诊/调查/SOAR/UEBA/威胁狩猎），不能只填运维场景
2. **不能纯 LLM**（C-4）：必须 LLM + DSLM + ML/统计/图算法混合，纯 Prompt 包装不准合并
3. **Multi-Agent 必须有 Orchestrator**（C-5）：禁止 itops-agent-platform 那种 9 个扁平 Agent 的反模式
4. **抑制幻觉三件套**（C-24/26/27）：LLM 输出含具体数据**必附引用**、Agent **必须能说"不知道"**、高风险动作**必双模型 cross-check**
5. **Prompt Injection 防护**（C-20）：用户输入 / 外部日志进 LLM 前必须沙箱化，**禁止裸字符串拼接**

完整 **34 条铁律**见 [CONSTRAINTS.md](CONSTRAINTS.md)（九大类）：
- 一、AISecOps 名实相符 · 二、AI 架构够格 · 三、安全与治理
- 四、数据层不玩具化 · 五、工程纪律 · 六、安全开发
- 七、抑制 LLM 幻觉 · 八、完善中文注释 · 九、AI 工程化

设计原则见 [PRINCIPLES.md](PRINCIPLES.md)。

## 文件导航

| 找什么 | 去哪 |
|---|---|
| 项目总览 + Roadmap | [README.md](README.md) |
| **需求文档 PRD** | [docs/specs/PRD.md](docs/specs/PRD.md) |
| **技术设计方案** | [docs/specs/technical-design.md](docs/specs/technical-design.md) |
| **开发计划** | [docs/specs/dev-plan.md](docs/specs/dev-plan.md) |
| **功能验收清单（"完成"判定）** | [docs/specs/feature-acceptance.md](docs/specs/feature-acceptance.md) |
| **系统兼容性矩阵** | [docs/specs/compatibility.md](docs/specs/compatibility.md) |
| **前端设计语言规范（L01）** | [docs/design/frontend-design-language.md](docs/design/frontend-design-language.md) |
| **架构 V2 文字版（视觉权威）** | [docs/architecture-v2.md](docs/architecture-v2.md) |
| 架构 V1 PNG（已过时，仅历史参考） | ~~docs/architecture.png~~ — superseded，见 [ADR-0002](docs/adr/0002-architecture-v2-supersedes-png.md) |
| 12 层精炼说明（给 AI 用） | [.claude/context/architecture.md](.claude/context/architecture.md) |
| 安全 / AI 术语表 | [.claude/context/glossary.md](.claude/context/glossary.md) |
| 硬铁律 | [CONSTRAINTS.md](CONSTRAINTS.md) |
| 软原则 | [PRINCIPLES.md](PRINCIPLES.md) |
| 架构决策记录 | [docs/adr/](docs/adr/) |
| 工作流约定 | [AGENTS.md](AGENTS.md) |
| 某一层细节 | `src/aisecops/L0X_*/README.md` |

## 工作流速查

- **要新增外部工具（L06）**：用 `/add-mcp <category> <name>` 生成骨架，**不要手写**。默认产**薄适配器**；只有确需远程/授权握手才加 `--full` 产完整 MCP Server（见 [ADR-0004](docs/adr/0004-l06-mcp-optional-thin-adapter.md)）
- **要新增 L02 Agent**：用 `/add-agent <role>` 一键生成骨架
- **要验证某层完整度**：用 `/verify-layer L0X`
- **跨层调用**：禁止跨层直连（如 L07 直接调 L10），必须经 L02 Orchestrator 编排或 L08 算法层
- **写代码前**：默认读 `src/aisecops/L0X_*/README.md` 确认子组件清单与业界对标

## 风格与偏好（用户硬性要求）

- 中文注释 + 中文 README，**不要科技风、不要堆术语**
- 解释一律以"对标业界基线"为切入点（用户对 AISecOps 业界很了解，喜欢这个口径）
- 零运维理念：能用托管/Serverless 不用自维护
- 不要把秘密/凭证/模型权重提交进仓库
- 与架构冲突时一律以 [docs/architecture-v2.md](docs/architecture-v2.md) 文字权威为准（V1 PNG 已 superseded，见 ADR-0002）
- **🚫 禁假按钮 + 整体可用（硬要求）**：功能必须**真实可用**——有真后端逻辑、可操作(CRUD/动作)、写动作留痕(C-23)、持久化(P-18)，详见 [功能验收清单](docs/specs/feature-acceptance.md)。**禁止"点了只弹提示、实则啥也没干"的假按钮**（要么真生效，要么标"未实现"并禁用）。菜单不做孤岛，要串成业务闭环（采集→降噪→分诊→关联→调查→处置→外发→工单→报表）。"功能完成"以 [DoD §8.0](docs/specs/dev-plan.md) 为准。

## 当前 git 状态

- 远端：https://github.com/hk17178/AISecOps (private)
- 主分支：main
- 用户：muzi <muzi0204@hotmail.com>

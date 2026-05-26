# CLAUDE.md · 项目对话上下文

> 本文件每次对话自动加载。**不要超过 200 行**——长了就改放 `.claude/context/`。

## 项目一句话

AISECOPS 是一个对标 Microsoft Security Copilot / CrowdStrike Charlotte / 奇安信 QAX-GPT 的国产 **AI 驱动安全运营平台**，按 12 层架构组织，从立项起就把"SEC"做成一等公民——不是 AIOps + Chat 的套壳。

## 当前阶段

🟡 **架构骨架阶段** —— 12 层目录与文档已就位，**代码 0 行**。

下一步 P0：L05 LLM Gateway + L02 Orchestrator + 1 个 MCP Server + L07 告警分诊端到端 demo。详见 [README.md](README.md) 的 Roadmap。

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
| **系统兼容性矩阵** | [docs/specs/compatibility.md](docs/specs/compatibility.md) |
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

- **要新增 MCP Server**：用 `/add-mcp <name>` 一键生成骨架，**不要手写**
- **要新增 L02 Agent**：用 `/add-agent <role>` 一键生成骨架
- **要验证某层完整度**：用 `/verify-layer L0X`
- **跨层调用**：禁止跨层直连（如 L07 直接调 L10），必须经 L02 Orchestrator 编排或 L08 算法层
- **写代码前**：默认读 `src/aisecops/L0X_*/README.md` 确认子组件清单与业界对标

## 风格与偏好（用户硬性要求）

- 中文注释 + 中文 README，**不要科技风、不要堆术语**
- 解释一律以"对标业界基线"为切入点（用户对 AISecOps 业界很了解，喜欢这个口径）
- 零运维理念：能用托管/Serverless 不用自维护
- 不要把秘密/凭证/模型权重提交进仓库
- 与架构图冲突时一律以 PNG 为准

## 当前 git 状态

- 远端：https://github.com/hk17178/AISecOps (private)
- 主分支：main
- 用户：muzi <muzi0204@hotmail.com>

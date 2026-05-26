# AGENTS.md · AI 工作流约定

> 给 Claude（以及未来其他 Agent IDE）的"工作守则"。本文不重复 CLAUDE.md 的内容，专讲**怎么做事**。

## 黄金法则

> **先读 README，再写代码；先查铁律，再做决策；先问场景，再选方案。**

## 项目结构思维

12 层架构 = 12 个**职责清晰的边界**。修改任何代码前，先问自己：

1. 这是 L 几的事？（看 `src/aisecops/L0X_*/README.md`）
2. 我会不会跨层调用？（**禁止**——见 PRINCIPLES.md "分层隔离"）
3. 我做的事在业界 AISecOps 基线里是哪个能力？（看每层 README 的"业界对标"段）

## 查找代码的优先级

| 场景 | 用什么工具 |
|---|---|
| 找文件路径 | Glob |
| 找符号 / 关键词 | Grep |
| 跨多文件研究 | Explore subagent |
| 设计阶段（暂无代码） | 直接读 README + CONSTRAINTS |
| 业界对标查证 | WebSearch（仅当不确定基线时） |

## 子代理（项目专属）

| Subagent | 何时调用 |
|---|---|
| `security-analyst` | 设计 L07 SecOps 业务能力、审查"是否真做了 SEC 而不是 OPS" |
| `mcp-builder` | 新建 / 审查 L06 MCP Server |
| `layer-architect` | 跨层调用审查、新功能落点决策 |

## 测试约定

- **集成测试不 mock 外部安全工具**（沿用 EHR 项目教训：mock 通过 ≠ 真接通）
- **L05 LLM Gateway 必须有 stub mode**：避免每次跑测试都烧 token
- **L08 算法引擎单测覆盖率 ≥ 80%**：算法层是 AISecOps 灵魂，不能含糊
- 测试目录 `tests/` 镜像 `src/aisecops/L0X_*` 组织
- 用 pytest，禁用 unittest

## 提交约定

- Commit message **用总结短语，不用数字编号**（用户硬性偏好）
- 主题不同就拆 commit；同主题的小改动合并
- 任何 secrets、模型权重、原始日志数据**绝不入库**（已在 .gitignore 兜底）
- `git push --force` 默认 deny（settings.json 已挡）

## 何时问、何时做

| 情形 | 默认动作 |
|---|---|
| 读 / Grep / Glob / WebFetch | 直接做，不问 |
| 单文件 Edit（已读过） | 直接做 |
| 新增文件、新增依赖 | **先问**——确认放哪一层、用什么库 |
| 跨层引入新概念 | **先问 + 写 ADR** |
| 任何动到 git 远端、删除文件、修改 settings | **必须问** |

## Slash Commands

- `/add-mcp <name>` — 在 L06 下一键创建 MCP Server 骨架
- `/add-agent <role>` — 在 L02 下一键创建 Agent 骨架
- `/verify-layer L0X` — 检查某层文件完整度与跨层调用合规

## 风格速查

- 用中文写代码注释与文档（用户硬性要求）
- 函数命名英文 snake_case（Python 规范）
- Docstring 用中文，简短一句话即可
- 禁止"防御性代码"——内部模块互信任，只在系统边界（用户输入、外部 API）做校验
- 禁止"为未来抽象"——三处相似代码再抽象，不要提前

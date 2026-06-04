# 重启手册 · 5 分钟重新上手

> 给"3 个月后忘了一切的自己"。放下多久回来，照这页走一遍就能继续。
> 版本：v1（S1 阶段）· 更新：2026-06-04

## 这是什么项目

AISECOPS = **自建自用**的 AI 驱动安全运营工具（10-100 人小团队用），按 12 层架构组织，SEC 是一等公民。
定位见 [ADR-0003](adr/0003-self-use-positioning.md)，铁律见 [CONSTRAINTS.md](../CONSTRAINTS.md)。

## 5 分钟起步

```bash
# 1. 进目录
cd AISECOPS

# 2. 装环境（需先有 uv：brew install uv）
make venv        # 建 .venv（Python 3.11）
make install     # 装依赖（含 dev）

# 3. 自检：一把过 lint + type + test
make check       # 全绿 = 环境 OK

# 4. 起数据层（Docker 运行时用 Colima，见 ADR-0010）
colima start     # 起 Docker daemon（首次下载 VM 镜像）
make dev         # PG(pgvector) + Redis
make obs         # 额外起 Prometheus/Grafana/OTel（http://localhost:3000）
colima stop      # 不用时停
```

> ⚠️ **Docker = Colima**（非 Docker Desktop）。`make check` 不需要 Docker（纯 Python + stub）；只有 `make dev/obs` 要先 `colima start`。
> 首次装：`brew install colima docker docker-compose` + 链 compose 插件 + 删 `~/.docker/config.json` 的 `credsStore`（详见 ADR-0010）。
> ⚠️ **凭证**：`cp .env.example .env` 后填真实密码/Key。`.env` 已 gitignore，**绝不入库**。

## 常用命令（`make` 看全部）

| 命令 | 作用 |
|---|---|
| `make check` | lint + type + test 一把过（= 本地版 CI） |
| `make test` | 只跑测试（stub，不烧 token） |
| `make fmt` | ruff 自动格式化 |
| `make dev` / `make down` | 起 / 停数据层 |

## 关键文件去哪找

| 找什么 | 去哪 |
|---|---|
| 对话上下文（每次自动加载） | [CLAUDE.md](../CLAUDE.md) |
| 需求 / 技术设计 / 开发计划 | [docs/specs/](specs/) |
| **下一步要做的 L05 计划** | [docs/specs/L05-impl-plan.md](specs/L05-impl-plan.md) |
| 架构（文字权威） | [docs/architecture-v2.md](architecture-v2.md) |
| 铁律 / 原则 | [CONSTRAINTS.md](../CONSTRAINTS.md) · [PRINCIPLES.md](../PRINCIPLES.md) |
| 架构决策记录 | [docs/adr/](adr/) |
| 前端设计语言 + 活样板 | [docs/design/](design/) |
| 某一层细节 | `src/aisecops/L0X_*/README.md` |

## 当前进度（2026-06-04）

- ✅ **M0** 12 层骨架 + 文档
- 🟡 **S1 基础设施**：环境/Docker 文件/CI/Makefile/OTel/本手册 已完成；
  - ⏳ 待办：装 Docker 后跑通 `make dev`；5 条 PRD §9 待决策（见下）
- 🔜 **下一步 = S2 写 L05 LLM Gateway**（计划见 L05-impl-plan.md，S0→S12）

## 还欠的决策（PRD §9，需真实环境信息才能定）

1. 跑在哪（机房/公司云/笔记本）
2. 接什么数据源（你们的 SIEM/EDR/防火墙是哪个）
3. LLM 选哪个（豆包/通义/智谱/本地 Qwen）→ 影响 L05 第一个 provider
4. 通知用什么（企微/钉钉/邮件）
5. CMDB 现状（Excel/Wiki/专门系统）

> 定了就各写一份 ADR（编号从 0009 起）。

## 协作约定

- main 已开**分支保护**：协作者（daimingyan）必须开 PR + 1 评审才能合，不能直推。
- PR 进来自动跑 CI（lint/type/test）。审查可叫 `layer-architect` / `security-analyst` 子智能体。

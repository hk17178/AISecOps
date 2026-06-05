# ADR-0011 · L01 作为组合根 + HTTP 表现层（拆 api.py 巨石 / 厘清越级直连）

- 状态：已接受
- 日期：2026-06-05
- 相关：架构一致性审计（P0.1 / P0.2 / P0.3）、[ADR-0008 跨层依赖 DAG](0008-cross-layer-dependency-dag.md)

## 背景

架构一致性审计指出三个 L01 层边界问题：

1. **P0.1 巨石文件**：`L01_human_interface/api.py` 长 1418 行，在 L01 目录里却初始化并定义了 L02–L12 几乎所有层的 store/service 与全部 REST 端点，单一职责被严重破坏。
2. **P0.2 越级直连**：`api.py` 直接 `import` 了 `normalize_alert`(L10)、`build_asset_store`(L11)、`build_prompt_store`(L04) 等，看似绕过了 ADR-0008 的允许边。
3. **P0.3 前端游离**：React 前端在仓库根 `frontend/`，不在 `src/aisecops/L01_*/` 层目录内，导致层审计失真。

## 决策

**L01 既是「组合根（Composition Root）」，也是「HTTP 表现层」。** 据此重构，不改变运行行为：

### 1. 组合根 = `L01_human_interface/runtime.py`

按 clean-architecture，**最外层装配内层是合规的**（依赖方向仍由外指内）。平台所有 L02–L12 的实例在 `runtime.py` 的 `Runtime` 单例里构建并持有（`rt`）。这把"装配"从"路由"里剥离。

> **因此 P0.2 的"越级直连"被正式厘清**：组合根天然要 wire 所有层，这是组合根的职责，**不算违反 ADR-0008**。ADR-0008 约束的是"业务运行时调用链"——而业务流仍走允许边：分诊/调查/关联经 L02 Orchestrator + L07 出口；只有"薄 CRUD 读仓储"（如列资产、列 IoC）由表现层直接读 repository，这是表现层读仓储的正常模式，不是业务越级。

### 2. HTTP 表现层 = `L01_human_interface/routers/*.py`

REST 路由是表现层关注点，**留在 L01**，但按域拆成多个 `APIRouter`（alerts / tickets / soar / dispatch / reports / assets / intel / prompts / agents / tools / routing / auth / config / system / triage_chat / investigation）。

> **关键好处**：HTTP/FastAPI 知识**只**留在 L01。L02–L12 保持"框架无关"——不 import FastAPI，可单测、可换协议、可复用。这比"把 router 塞进各数据层"更干净（数据层不该知道 HTTP）。

`api.py` 退化为薄装配：建 `app` → `include_router` 所有域 → 导出 `app`（及测试用的 `get_*` 依赖）。

### 3. 前端 `frontend/` 正式归属 L01

`frontend/`（React 暖纸台）是 L01 人机交互的实现，在 `L01_human_interface/README.md` 中正式认领其为 L01 的前端实现路径。不物理移入（避免破坏既有构建/CI 路径），以文档认领消除审计盲区。

## 后果

- ✅ api.py 从 1418 行 → 薄装配；各域 router 独立可读。
- ✅ L02–L12 框架无关性显式化（HTTP 只在 L01）。
- ✅ "越级直连"有了明确定性：组合根 wire 全层合规；业务链走允许边。
- ⚠️ `runtime.py` 是单例组合根，进程内全局状态；测试经 `app.dependency_overrides` 覆盖依赖（`get_gateway` / `get_triage_service` 等保持可从 `api` import）。

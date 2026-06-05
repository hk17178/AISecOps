# L01 · 人机交互层 (Human Interface)

## 职责
对外提供分析师、管理员、最终用户的可视化与对话入口，承接 SOC tier-1/tier-2 的日常操作面。

## 子组件
- **告警面板 (Alert Console)** —— 告警分诊视图，对接 L07 alert_triage
- **工单 UI (Ticket Console)** —— 安全事件工单与处置流转，对接 L02 platform_core 工单引擎
- **报表 UI (Report Console)** —— 自动报告、合规报告、MTTD/MTTR 仪表盘
- **Chat 面板 (Conversational Console)** —— 自然语言调查入口，对接 L02 Orchestrator
- **移动端 / Web Console** —— 多端响应

## 实现路径（重要）

L01 由三部分构成（见 [ADR-0011](../../../docs/adr/0011-l01-composition-root-and-routers.md)）：

| 部分 | 位置 | 说明 |
|---|---|---|
| **React 前端** | **仓库根 `frontend/`** | 暖纸安全运营台，17 项 IA 全部实页。**它在物理上不在本目录，但架构归属 L01**（构建/CI 路径历史原因留在根目录，以此文档正式认领，消除审计盲区） |
| **组合根** | `runtime.py` | `Runtime` 单例 `rt`，装配 L02–L12 所有 store/service（组合根 wire 全层合规） |
| **HTTP 表现层** | `routers/*.py` | 按域拆分的 FastAPI `APIRouter`；`api.py` 仅做薄装配（建 app + include_router + 静态文件） |

> HTTP/FastAPI 知识**只**在 L01；L02–L12 保持框架无关。

## 业界对标
- Microsoft Security Copilot 的 Standalone & Embedded experience
- CrowdStrike Falcon Console + Charlotte AI Chat
- 奇安信 QAX-GPT 的安全工作台

## 当前状态
🟢 前端 17 项 IA 接真；后端按 ADR-0011 拆为 runtime(组合根) + routers/(各域) + api.py(薄装配)。

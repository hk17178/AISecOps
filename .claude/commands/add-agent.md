---
description: 在 L02 下一键生成 AI Agent 骨架。用法：/add-agent <role>，如 /add-agent triage 或 /add-agent intel
allowed-tools: Write, Read, Glob, Bash, PowerShell
---

**参数**：`$ARGUMENTS`
- Agent role 名（小写）。标准角色：orchestrator / triage / investigation / enrichment / responder / reporter / intel / tuning。其他自定义角色需在 README 说明。

**任务**：
1. 检查 `src/aisecops/L02_agents/<role>/` 是否存在，如已存在请确认是否覆盖
2. 创建：
   - `__init__.py`
   - `agent.py` —— Agent 主体骨架
   - `prompts/system.md` —— 系统 Prompt（中文）
   - `tools.py` —— 该 Agent 能调用的 tool 清单
   - `README.md` —— 包含职责、业界对标、与其他 Agent 的协作关系
   - `tests/test_<role>_agent.py` —— 单测占位
3. `agent.py` 中：
   - 不要直接调 LLM，必须经 `L05_gateway/llm_gateway/`
   - 暴露 `async def run(task) -> Result` 接口
   - 保留 `memory_store` 注入点（L02 platform_core）
4. README 必须列：
   - Agent 角色定位（业界对标）
   - 上游谁调它、下游它调谁
   - HITL 边界（哪些动作需要人审）

**铁律提醒**：
- Orchestrator 之外的 Agent **禁止互相直接调用**，必须经 Orchestrator
- 任何处置动作（写操作）必须先经 HITL
- Responder Agent 必须把待处置动作放入工单引擎，不能直接执行

最后告诉用户：
- 文件路径
- Orchestrator 注册位置（提醒在哪改）
- 下一步要补 prompt / tool / 测试

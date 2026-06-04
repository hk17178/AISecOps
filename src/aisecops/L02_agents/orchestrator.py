"""L02 · Orchestrator —— 任务分解 / 路由 / 聚合（P-7：只编排，不做业务推理）。

禁止 itops 那种 9 个扁平 Agent 的反模式（C-5）：所有任务必经 Orchestrator 调度。
"""

from __future__ import annotations

from .base import Agent, AgentContext, AgentResult, Task


class OrchestratorError(Exception):
    """编排错误（如没有能处理该任务的 Agent）。"""


class Orchestrator:
    """按任务类型把任务路由给对应 Agent。"""

    def __init__(self, agents: dict[str, Agent], ctx: AgentContext) -> None:
        # key = task.kind，value = 处理它的 Agent
        self.agents = agents
        self.ctx = ctx

    def _route(self, task: Task) -> Agent:
        agent = self.agents.get(task.kind)
        if agent is None:
            raise OrchestratorError(f"没有能处理任务类型 '{task.kind}' 的 Agent")
        return agent

    async def dispatch(self, task: Task) -> AgentResult:
        """把任务路由给对应 Agent 并执行。"""
        agent = self._route(task)
        self.ctx.audit.append(actor="orchestrator", action="dispatch", target=task.kind)
        return await agent.run(task, self.ctx)

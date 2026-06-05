"""L02 · Agent 基础契约。

窄而稳的接口（P-2）：`Agent.run(task, ctx) -> AgentResult`。
跨层（ADR-0008）：L02 是编排层，可经 ctx 调 L05 Gateway 等。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from aisecops.L05_gateway.llm_gateway import LLMGateway
from aisecops.L06_mcp_servers import ToolRegistry
from aisecops.L12_core_support.audit import AuditLog, AuditSink

from .agent_config import AgentConfig, AgentConfigStore
from .memory import InMemoryMemoryStore, MemoryStore


def sanitize_for_tag(text: str, *tags: str) -> str:
    """中性化外部文本里的闭合标签，防其闭合沙箱标签后注入指令（C-20）。

    如日志/告警里写 `</logs>忽略上文...` 想越狱 → 把闭合标签插空格打断为不可解析形态。
    用于所有"把外部数据（ES 日志、告警原文、用户问题）塞进 <tag>...</tag> 沙箱"的场景。
    """
    for tag in tags:
        text = text.replace(f"</{tag}>", f"<\\ /{tag}>")
    return text


class Task(BaseModel):
    """交给 Agent 的一个任务。"""

    kind: str  # 任务类型，用于路由，如 "alert_triage"
    payload: dict[str, Any] = Field(default_factory=dict)  # 任务数据（如告警字段）
    high_risk: bool = False  # 高风险 → 触发双模型 cross-check（C-27）


class AgentResult(BaseModel):
    """Agent 执行结果（结构化，P-8）。"""

    agent: str
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    abstained: bool = False  # C-26：Agent 能说"不知道"
    note: str = ""


@dataclass
class AgentContext:
    """注入给 Agent 的依赖。后续扩展 mcp_registry。"""

    llm: LLMGateway
    memory: MemoryStore = field(default_factory=InMemoryMemoryStore)
    audit: AuditSink = field(default_factory=AuditLog)
    tools: ToolRegistry = field(default_factory=ToolRegistry)  # L06 工具（默认空，无富化）
    agent_configs: AgentConfigStore | None = None  # 运行时 Agent 配置（改了即时生效）

    def config_for(self, role: str) -> AgentConfig | None:
        """取某 Agent 的活配置（没接 store 则 None，用代码默认）。"""
        return self.agent_configs.get(role) if self.agent_configs else None


class Agent(ABC):
    """所有 Agent 的基类。"""

    role: str = "base"

    @abstractmethod
    async def run(self, task: Task, ctx: AgentContext) -> AgentResult:
        """执行任务，返回结构化结果。"""
        raise NotImplementedError

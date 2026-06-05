"""L02 · Tuning Agent —— 反馈飞轮引擎（architecture-v2 ★反馈飞轮）。

飞轮：L01 工单/调查结案 ──事件──▶ L02 Tuning Agent ──▶ L03 知识库（去重沉淀）→ 下一轮
Triage/Investigation 自动 RAG 召回 → 研判更准。这是 V2 里唯一合法的"向上"回流（事件驱动）。

Tuning 只**沉淀**与**给调优建议**，不自动改阈值（留人确认，HITL 精神）。确定性，非纯 LLM。
跨层：L02→L03（经知识库门面），DAG 合规。
"""

from __future__ import annotations

from aisecops.L03_ai_assets_rag import KnowledgeBase

from .base import Agent, AgentContext, AgentResult, Task


class TuningAgent(Agent):
    """反馈飞轮：把结案的处理记录沉淀进知识库（去重）。"""

    role = "tuning"

    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    async def run(self, task: Task, ctx: AgentContext) -> AgentResult:
        case = task.payload
        title = str(case.get("title", "")).strip()
        content = str(case.get("content", "")).strip()
        source = str(case.get("source", ""))
        category = str(case.get("category", "历史告警处理记录"))
        if not title or not content:
            return AgentResult(agent=self.role, ok=True, data={"sunk": False, "reason": "空案例"}, note="无内容可沉淀")
        # 去重：同 source（工单/调查 ID）已沉淀则跳过，避免飞轮重复灌入
        if source and any(d.source == source for d in self._kb.store.all()):
            return AgentResult(agent=self.role, ok=True, data={"sunk": False, "reason": "已沉淀"}, note="重复，跳过")
        doc = self._kb.add_doc(title, category, content, source=source)
        ctx.audit.append(
            actor=self.role, action="knowledge_sink", target=doc.id, details={"source": source, "category": category}
        )
        return AgentResult(agent=self.role, ok=True, data={"sunk": True, "doc_id": doc.id})

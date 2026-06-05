"""L02 · Intel Agent —— 威胁情报富化（C-25：能查就别让 LLM 凭记忆）。

确定性：把告警字段与 IoC 库比对，给出命中情报。供 Enrichment/Triage 引用，不臆造。
跨层：L02→L08（读情报库与匹配算法），DAG 合规。
"""

from __future__ import annotations

from aisecops.L08_analytics_engines import IocStore, match_iocs

from .base import Agent, AgentContext, AgentResult, Task


class IntelAgent(Agent):
    """威胁情报富化 Agent。"""

    role = "intel"

    def __init__(self, ioc_store: IocStore) -> None:
        self._iocs = ioc_store

    async def run(self, task: Task, ctx: AgentContext) -> AgentResult:
        hits = match_iocs(task.payload, self._iocs.all())
        data = {
            "ioc_hits": [{"id": i.id, "value": i.value, "type": i.type, "severity": i.severity} for i in hits],
            "hit_count": len(hits),
        }
        ctx.audit.append(
            actor=self.role,
            action="intel_enrich",
            target=str(task.payload.get("host", "")),
            details={"hits": len(hits)},
        )
        return AgentResult(agent=self.role, ok=True, data=data)

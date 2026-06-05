"""L02 · Enrichment Agent —— 上下文富化（确定性聚合，C-4 非纯 LLM）。

把一条告警的"周边事实"聚到一起喂给研判：CMDB 资产重要度/角色 + IoC 命中 + 历史处置经验(RAG)。
让 Triage 在有据可依的上下文上判，而不是裸看一条告警。

跨层：L02→L08(IoC) / L02→L03(RAG，经 ctx) 合规；CMDB 属 L11（L02 不可直连）→ 用**依赖注入**
的 asset_lookup（组合根传入 rt.assets.get_by_host），不静态 import L11。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aisecops.L08_analytics_engines import IocStore, match_iocs

from .base import Agent, AgentContext, AgentResult, Task

# 注入的资产查询：host -> 资产对象(含 importance/role)或 None
AssetLookup = Callable[[str], Any]


class EnrichmentAgent(Agent):
    """上下文富化 Agent。"""

    role = "enrichment"

    def __init__(self, asset_lookup: AssetLookup, ioc_store: IocStore) -> None:
        self._asset_lookup = asset_lookup
        self._iocs = ioc_store

    async def run(self, task: Task, ctx: AgentContext) -> AgentResult:
        host = str(task.payload.get("host", ""))
        context: dict[str, Any] = {}

        # CMDB 资产（依赖注入，不直连 L11）：关键/高资产是升级高风险的依据
        asset = self._asset_lookup(host) if host else None
        if asset is not None:
            context["asset"] = {"importance": asset.importance, "role": asset.role}

        # IoC 命中（L08）
        hits = match_iocs(task.payload, self._iocs.all())
        if hits:
            context["ioc_hits"] = [{"value": i.value, "type": i.type, "severity": i.severity} for i in hits]

        # 历史处置经验（L03 RAG，带出处）
        if ctx.rag is not None:
            kb = ctx.rag.search(f"{host} {task.payload.get('title', '')}".strip(), top_k=3)
            if kb:
                context["kb"] = [{"doc_id": h.doc_id, "title": h.title, "text": h.text} for h in kb]

        ctx.audit.append(actor=self.role, action="enrich", target=host, details={"keys": list(context.keys())})
        return AgentResult(agent=self.role, ok=True, data={"context": context})

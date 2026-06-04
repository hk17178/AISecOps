"""L05 · 场景 → 模型路由（按功能分配大模型，§4.4）。

对标业界基线：Charlotte/Copilot 都按"任务难度/成本"把不同环节路由到不同档位的模型
——便宜本地模型扛高频低风险（分诊降噪），强模型扛高价值推理（调查/关联/报告）。

本表只决定"优先用哪个 provider"，命中的排到队首，其余按原序作降级兜底（C-34），
stub 永远在最后。匹配规则：scenario 精确命中优先，否则取最长前缀/子串命中，再否则用默认。
"""

from __future__ import annotations

from .providers.base import Provider


class ScenarioRouter:
    """场景→provider 名的路由表。规则可增删改（CRUD），由上层持久化。"""

    def __init__(self, routes: dict[str, str] | None = None, default: str | None = None) -> None:
        self._routes: dict[str, str] = dict(routes or {})
        self.default = default

    # ---- 查询 ----
    def provider_name_for(self, scenario: str) -> str | None:
        """该场景命中的 provider 名（未命中返回 default）。"""
        if scenario in self._routes:
            return self._routes[scenario]
        best_key: str | None = None
        for key in self._routes:
            if (scenario.startswith(key) or key in scenario) and (best_key is None or len(key) > len(best_key)):
                best_key = key
        return self._routes[best_key] if best_key is not None else self.default

    def order(self, scenario: str, providers: list[Provider]) -> list[Provider]:
        """把命中的 provider 排到队首，其余保序作降级；未命中或找不到则原序返回。"""
        name = self.provider_name_for(scenario)
        if not name:
            return list(providers)
        hit = [p for p in providers if p.name == name]
        if not hit:
            return list(providers)  # 路由指向的模型当前不可用 → 不强行改序，走原降级链
        rest = [p for p in providers if p.name != name]
        return hit + rest

    # ---- CRUD ----
    def set_route(self, scenario: str, provider_name: str) -> None:
        self._routes[scenario] = provider_name

    def remove_route(self, scenario: str) -> bool:
        return self._routes.pop(scenario, None) is not None

    def as_dict(self) -> dict[str, str]:
        return dict(self._routes)


# 默认路由表（业界口径的分档）。provider 名对应 LLM_PROFILES 里配置的 name；
# 没配多 profile 时这些名字命中不到，会自动回退默认 provider（order() 原序），不报错。
DEFAULT_ROUTES: dict[str, str] = {
    # 高频低风险：便宜/快模型
    "L07/alert_triage": "快",
    "L07/alert_dedupe": "快",
    "L01/chat": "快",
    # 高价值推理：强模型
    "L07/investigation": "强",
    "L08/correlation": "强",
    "L07/threat_hunting": "强",
    # 报告生成：可单独配
    "L07/report": "强",
}

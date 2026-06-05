"""L11 · AI 资产合规 / Shadow AI 治理（C-3）。

2026 业界基线把"AI 资产本身"纳入被监测对象：组织里用了哪些 LLM/模型/AI 服务、是否经审批、
是否出域、能处理什么敏感级、风险等级几何。本模块提供：
1. **AI 资产清单**（仓储模式 PG/内存，与 CMDB 一致）；
2. **合规检查引擎**（确定性规则，对标《生成式AI服务管理办法》/EU AI Act 风险分级）；
3. **Shadow AI 发现**：把平台实际在用的 LLM provider（L05 网关）与已审批清单比对，
   未登记的即影子 AI 候选——平台先治理自己的 AI 用量。

确定性、可解释、非 LLM。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

# AI 资产类别
KINDS = ("LLM", "Embedding", "ML模型", "AI服务", "AI工具", "Agent")
# 审批状态
STATUS = ("已批准", "待评审", "影子")
# 数据敏感级（可处理的最高级）
SENSITIVITY = ("公开", "内部", "敏感", "机密")
# 风险分级（对标生成式AI管理办法 / EU AI Act）
RISK_CLASS = ("最小", "有限", "高", "不可接受")


class AiAsset(BaseModel):
    """一项 AI 资产。"""

    id: str
    name: str
    kind: str = "LLM"
    provider: str = ""
    endpoint: str = ""
    status: str = "待评审"
    owner: str = ""
    outbound: bool = False  # 是否出域（数据离境/到外部）
    sensitivity: str = "内部"  # 允许处理的最高数据敏感级
    risk_class: str = "有限"
    discovered: str = "人工登记"  # 人工登记 / 网关自动发现
    note: str = ""


class ComplianceFinding(BaseModel):
    """一条合规发现。"""

    asset_id: str
    asset_name: str
    severity: str  # P0 / P1 / P2
    rule: str
    message: str
    suggestion: str


_EDITABLE = ("name", "kind", "provider", "endpoint", "status", "owner", "outbound", "sensitivity", "risk_class", "note")


class AiAssetStore(ABC):
    @abstractmethod
    def all(self) -> list[AiAsset]: ...

    @abstractmethod
    def create(self, fields: dict[str, Any]) -> AiAsset: ...

    @abstractmethod
    def update(self, asset_id: str, fields: dict[str, Any]) -> AiAsset | None: ...

    @abstractmethod
    def remove(self, asset_id: str) -> bool: ...


def _coerce(fields: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in _EDITABLE:
        if k in fields and fields[k] is not None:
            out[k] = bool(fields[k]) if k == "outbound" else str(fields[k])
    return out


class InMemoryAiAssetStore(AiAssetStore):
    def __init__(self) -> None:
        self._items: list[AiAsset] = []

    def all(self) -> list[AiAsset]:
        return list(self._items)

    def create(self, fields: dict[str, Any]) -> AiAsset:
        seq = len(self._items) + 1
        a = AiAsset(
            id=f"AIA-{seq}",
            name=str(fields.get("name", "")),
            **_coerce({k: v for k, v in fields.items() if k != "name"}),
        )
        self._items.append(a)
        return a

    def update(self, asset_id: str, fields: dict[str, Any]) -> AiAsset | None:
        a = next((x for x in self._items if x.id == asset_id), None)
        if a is None:
            return None
        for k, v in _coerce(fields).items():
            setattr(a, k, v)
        return a

    def remove(self, asset_id: str) -> bool:
        before = len(self._items)
        self._items = [x for x in self._items if x.id != asset_id]
        return len(self._items) < before


class PgAiAssetStore(AiAssetStore):
    _COLS = "seq, name, kind, provider, endpoint, status, owner, outbound, sensitivity, risk_class, discovered, note"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS ai_assets ("
                "seq SERIAL PRIMARY KEY, name text, kind text, provider text, endpoint text, status text, "
                "owner text, outbound boolean DEFAULT false, sensitivity text, risk_class text, "
                "discovered text, note text)"
            )

    @staticmethod
    def _to_asset(r: Any) -> AiAsset:
        return AiAsset(
            id=f"AIA-{int(r[0])}",
            name=r[1] or "",
            kind=r[2] or "LLM",
            provider=r[3] or "",
            endpoint=r[4] or "",
            status=r[5] or "待评审",
            owner=r[6] or "",
            outbound=bool(r[7]),
            sensitivity=r[8] or "内部",
            risk_class=r[9] or "有限",
            discovered=r[10] or "人工登记",
            note=r[11] or "",
        )

    @staticmethod
    def _seq_of(aid: str) -> int:
        try:
            return int(aid.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[AiAsset]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM ai_assets ORDER BY seq").fetchall()
        return [self._to_asset(r) for r in rows]

    def create(self, fields: dict[str, Any]) -> AiAsset:
        c = _coerce(fields)
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO ai_assets (name, kind, provider, endpoint, status, owner, outbound, sensitivity, "
                "risk_class, discovered, note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING seq",
                (
                    str(fields.get("name", "")),
                    c.get("kind", "LLM"),
                    c.get("provider", ""),
                    c.get("endpoint", ""),
                    c.get("status", "待评审"),
                    c.get("owner", ""),
                    c.get("outbound", False),
                    c.get("sensitivity", "内部"),
                    c.get("risk_class", "有限"),
                    str(fields.get("discovered", "人工登记")),
                    c.get("note", ""),
                ),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return self._to_asset(
            (
                seq,
                fields.get("name", ""),
                c.get("kind", "LLM"),
                c.get("provider", ""),
                c.get("endpoint", ""),
                c.get("status", "待评审"),
                c.get("owner", ""),
                c.get("outbound", False),
                c.get("sensitivity", "内部"),
                c.get("risk_class", "有限"),
                fields.get("discovered", "人工登记"),
                c.get("note", ""),
            )
        )

    def update(self, asset_id: str, fields: dict[str, Any]) -> AiAsset | None:
        seq = self._seq_of(asset_id)
        sets = list(_coerce(fields).items())
        with self._pool.connection() as conn:
            if sets:
                clause = ", ".join(f"{k}=%s" for k, _ in sets)
                conn.execute(f"UPDATE ai_assets SET {clause} WHERE seq=%s", [v for _, v in sets] + [seq])
            row = conn.execute(f"SELECT {self._COLS} FROM ai_assets WHERE seq=%s", (seq,)).fetchone()
        return self._to_asset(row) if row else None

    def remove(self, asset_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM ai_assets WHERE seq=%s", (self._seq_of(asset_id),))
            return bool(cur.rowcount)


def check_compliance(asset: AiAsset, *, outbound_enabled: bool = False) -> list[ComplianceFinding]:
    """对单项 AI 资产跑确定性合规规则。"""
    out: list[ComplianceFinding] = []

    def add(sev: str, rule: str, msg: str, fix: str) -> None:
        out.append(
            ComplianceFinding(
                asset_id=asset.id, asset_name=asset.name, severity=sev, rule=rule, message=msg, suggestion=fix
            )
        )

    if asset.risk_class == "不可接受":
        add("P0", "禁止类AI", "属「不可接受风险」类别（监管禁止）", "立即停用，不得在生产使用")
    if asset.status == "影子":
        add("P1", "ShadowAI", "未经审批的影子 AI（绕过治理在用）", "评审登记或下线；接 L05 网关纳管")
    if asset.risk_class == "高" and asset.status != "已批准":
        add("P1", "高风险未批", "高风险 AI 未经审批即在用", "走高风险 AI 评审（安全/合规/法务）后再启用")
    if asset.outbound and asset.sensitivity in ("敏感", "机密"):
        add(
            "P1",
            "敏感出域",
            f"允许处理「{asset.sensitivity}」数据且出域，泄露面高",
            "数据出域前强制脱敏，或改用本地模型",
        )
    if asset.outbound and not outbound_enabled and asset.status == "已批准":
        add(
            "P2",
            "出域不一致",
            "标记为出域但平台出域开关关闭，调用会被网关拦截",
            "核对该资产是否真需出域，或开启受控出域",
        )
    if not asset.owner.strip():
        add("P2", "缺责任人", "AI 资产无责任人（问责缺口）", "指派属主，纳入资产台账")
    return out


def discover_shadow_ai(in_use_providers: list[dict[str, Any]], assets: list[AiAsset]) -> list[dict[str, Any]]:
    """把平台实际在用的 LLM provider 与已审批清单比对，未登记者=影子 AI 候选。

    in_use_providers: [{name, model, outbound}]（来自 L05 网关）。
    """
    approved = {a.name for a in assets if a.status == "已批准"}
    approved |= {a.provider for a in assets if a.status == "已批准" and a.provider}
    out: list[dict[str, Any]] = []
    for p in in_use_providers:
        name = str(p.get("name", ""))
        if p.get("stub"):
            continue  # 离线占位不算 AI 资产
        if name not in approved:
            out.append(
                {
                    "name": name,
                    "model": str(p.get("model", "")),
                    "outbound": bool(p.get("outbound", False)),
                    "reason": "在用的 LLM provider 未在已审批 AI 资产清单中",
                }
            )
    return out


def build_ai_asset_store(database_url: str = "") -> AiAssetStore:
    if database_url:
        try:
            return PgAiAssetStore(database_url)
        except Exception:
            pass
    return InMemoryAiAssetStore()


def seed_demo_ai_assets(store: AiAssetStore) -> None:
    if store.all():
        return
    store.create(
        {
            "name": "通义千问(分诊)",
            "kind": "LLM",
            "provider": "通义",
            "status": "已批准",
            "owner": "安全组",
            "outbound": False,
            "sensitivity": "敏感",
            "risk_class": "有限",
            "note": "国产、内网，分诊主力",
        }
    )
    store.create(
        {
            "name": "Claude(复核)",
            "kind": "LLM",
            "provider": "Anthropic",
            "status": "待评审",
            "owner": "",
            "outbound": True,
            "sensitivity": "敏感",
            "risk_class": "高",
            "note": "海外、高风险类，出域复核用，待评审",
        }
    )
    store.create(
        {
            "name": "某员工自用ChatGPT",
            "kind": "AI服务",
            "provider": "OpenAI",
            "status": "影子",
            "owner": "",
            "outbound": True,
            "sensitivity": "机密",
            "risk_class": "高",
            "discovered": "网关自动发现",
            "note": "发现有人把告警贴外部 ChatGPT",
        }
    )

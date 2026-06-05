"""L04 · Skills(SOP) 库 —— 结构化标准操作流程（ADR-0013）。

Skill = "怎么做某类事"的有序步骤 + 适用场景 + 引用，给 Agent/分析师当指引与 checklist（不自动执行；
自动处置是 L02 SOAR Playbook，二者分工见 ADR-0013）。仓储模式 PG/内存，与其它 store 一致。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

CATEGORIES = ("调查SOP", "处置SOP", "排障SOP", "合规SOP")


class Skill(BaseModel):
    """一个标准操作流程。"""

    id: str
    name: str
    category: str = "调查SOP"
    scenario: str = ""  # 适用场景关键词（如 勒索 / 横向移动 / investigation），匹配用
    steps: list[str] = Field(default_factory=list)
    refs: list[str] = Field(default_factory=list)
    enabled: bool = True
    version: int = 1


def match_skills(context_text: str, skills: list[Skill], limit: int = 3) -> list[Skill]:
    """按场景关键词匹配适用 SOP（确定性）。scenario 命中 context 文本即算适用。"""
    text = context_text.lower()
    hits = [s for s in skills if s.enabled and s.scenario and s.scenario.lower() in text]
    return hits[:limit]


class SkillStore(ABC):
    @abstractmethod
    def all(self) -> list[Skill]: ...

    @abstractmethod
    def create(self, fields: dict[str, Any]) -> Skill: ...

    @abstractmethod
    def update(self, skill_id: str, fields: dict[str, Any]) -> Skill | None: ...

    @abstractmethod
    def remove(self, skill_id: str) -> bool: ...


def _coerce(fields: dict[str, Any], cur: Skill | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "name" in fields and fields["name"] is not None:
        out["name"] = str(fields["name"])
    if fields.get("category") in CATEGORIES:
        out["category"] = fields["category"]
    if "scenario" in fields and fields["scenario"] is not None:
        out["scenario"] = str(fields["scenario"])
    for key in ("steps", "refs"):
        if key in fields and fields[key] is not None:
            out[key] = [str(x) for x in fields[key]]
    if "enabled" in fields and fields["enabled"] is not None:
        out["enabled"] = bool(fields["enabled"])
    return out


class InMemorySkillStore(SkillStore):
    def __init__(self) -> None:
        self._items: list[Skill] = []
        self._seq = 0

    def all(self) -> list[Skill]:
        return list(self._items)

    def create(self, fields: dict[str, Any]) -> Skill:
        self._seq += 1
        data: dict[str, Any] = {"name": "", "category": "调查SOP", "scenario": "", "steps": [], "refs": []}
        data.update(_coerce(fields))
        skill = Skill(id=f"SOP-{self._seq:03d}", **data)
        self._items.append(skill)
        return skill

    def update(self, skill_id: str, fields: dict[str, Any]) -> Skill | None:
        s = next((x for x in self._items if x.id == skill_id), None)
        if s is None:
            return None
        for k, v in _coerce(fields).items():
            setattr(s, k, v)
        s.version += 1
        return s

    def remove(self, skill_id: str) -> bool:
        before = len(self._items)
        self._items = [x for x in self._items if x.id != skill_id]
        return len(self._items) < before


class PgSkillStore(SkillStore):
    _COLS = "seq, name, category, scenario, steps, refs, enabled, version"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS skills ("
                "seq SERIAL PRIMARY KEY, name text, category text, scenario text, "
                "steps text, refs text, enabled boolean DEFAULT true, version integer DEFAULT 1)"
            )

    @staticmethod
    def _to_skill(r: Any) -> Skill:
        return Skill(
            id=f"SOP-{int(r[0]):03d}",
            name=r[1] or "",
            category=r[2] or "调查SOP",
            scenario=r[3] or "",
            steps=json.loads(r[4]) if r[4] else [],
            refs=json.loads(r[5]) if r[5] else [],
            enabled=bool(r[6]),
            version=int(r[7]),
        )

    @staticmethod
    def _seq_of(sid: str) -> int:
        try:
            return int(sid.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[Skill]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM skills ORDER BY seq").fetchall()
        return [self._to_skill(r) for r in rows]

    def create(self, fields: dict[str, Any]) -> Skill:
        c = _coerce(fields)
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO skills (name, category, scenario, steps, refs, enabled, version) "
                "VALUES (%s,%s,%s,%s,%s,true,1) RETURNING seq",
                (
                    c.get("name", ""),
                    c.get("category", "调查SOP"),
                    c.get("scenario", ""),
                    json.dumps(c.get("steps", []), ensure_ascii=False),
                    json.dumps(c.get("refs", []), ensure_ascii=False),
                ),
            ).fetchone()
        seq = int(row[0]) if row else 0
        data: dict[str, Any] = {"name": "", "category": "调查SOP", "scenario": "", "steps": [], "refs": []}
        data.update(c)
        return Skill(id=f"SOP-{seq:03d}", **data)

    def update(self, skill_id: str, fields: dict[str, Any]) -> Skill | None:
        seq = self._seq_of(skill_id)
        with self._pool.connection() as conn:
            cur = conn.execute(f"SELECT {self._COLS} FROM skills WHERE seq=%s", (seq,)).fetchone()
            if cur is None:
                return None
            c = _coerce(fields)
            merged = {
                "name": c.get("name", cur[1]),
                "category": c.get("category", cur[2]),
                "scenario": c.get("scenario", cur[3]),
                "steps": c.get("steps", json.loads(cur[4]) if cur[4] else []),
                "refs": c.get("refs", json.loads(cur[5]) if cur[5] else []),
                "enabled": c.get("enabled", bool(cur[6])),
            }
            conn.execute(
                "UPDATE skills SET name=%s, category=%s, scenario=%s, steps=%s, refs=%s, enabled=%s, version=%s "
                "WHERE seq=%s",
                (
                    merged["name"],
                    merged["category"],
                    merged["scenario"],
                    json.dumps(merged["steps"], ensure_ascii=False),
                    json.dumps(merged["refs"], ensure_ascii=False),
                    merged["enabled"],
                    int(cur[7]) + 1,
                    seq,
                ),
            )
            row = conn.execute(f"SELECT {self._COLS} FROM skills WHERE seq=%s", (seq,)).fetchone()
        return self._to_skill(row) if row else None

    def remove(self, skill_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM skills WHERE seq=%s", (self._seq_of(skill_id),))
            return bool(cur.rowcount)


def build_skill_store(database_url: str = "") -> SkillStore:
    if database_url:
        try:
            return PgSkillStore(database_url)
        except Exception:
            pass
    return InMemorySkillStore()


def seed_demo_skills(store: SkillStore) -> None:
    if store.all():
        return
    store.create(
        {
            "name": "勒索软件应急 SOP",
            "category": "处置SOP",
            "scenario": "勒索",
            "steps": [
                "立即网络隔离受影响主机",
                "保留内存与磁盘镜像取证",
                "排查横向移动来源账号",
                "确认备份完好再评估恢复",
            ],
            "refs": ["复盘归档/勒索案例"],
        }
    )
    store.create(
        {
            "name": "横向移动调查 SOP",
            "category": "调查SOP",
            "scenario": "横向移动",
            "steps": [
                "梳理涉事账号近期登录",
                "查 PsExec/WMI/RDP 远程执行痕迹",
                "定位首个被控主机(patient zero)",
                "封锁被滥用凭证",
            ],
            "refs": [],
        }
    )

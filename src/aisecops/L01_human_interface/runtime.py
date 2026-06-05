"""L01 · 组合根（Composition Root）。

整个平台的装配点：把 L02–L12 各层的 store/gateway/service 在这里构建并持有。
按 clean-architecture，最外层(L01)组合内层是合规的（见 ADR-0011）。各 REST router
（routers/*.py）只读这里的 `rt` 单例 + Depends 函数，不再各自重建依赖。

下层(L02–L12)保持框架无关：本文件不含任何 FastAPI/HTTP 知识，HTTP 在 routers/ 里。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aisecops.L02_agents import (
    AgentContext,
    build_agent_config_store,
    build_channel_store,
    build_dispatch_rule_store,
    build_playbook_store,
    SessionStore,
    build_record_store,
    build_run_store,
    build_ticket_store,
    build_user_store,
    seed_agent_configs,
    seed_demo_channels_rules,
    seed_demo_playbooks,
    seed_demo_tickets,
    seed_demo_users,
)
from aisecops.L03_ai_assets_rag import build_knowledge_base, seed_demo_knowledge
from aisecops.L04_ai_assets_models import build_prompt_store, seed_demo_prompts
from aisecops.L05_gateway.llm_gateway import (
    LLMGateway,
    ScenarioRouter,
    build_gateway,
    build_route_store,
    seed_default_routes,
)
from aisecops.L06_mcp_servers import (
    build_adapter_store,
    build_notifier,
    build_tool_registry,
    seed_demo_adapters,
)
from aisecops.L07_secops_capabilities import (
    AlertTriageService,
    CorrelationService,
    InvestigationService,
    build_alert_triage_service,
    build_correlation_service,
    build_ingest_service,
    build_investigation_service,
    build_reporting_service,
)
from aisecops.L10_data_collection.ingest import normalize_alert
from aisecops.L08_analytics_engines import (
    DedupEngine,
    build_ioc_store,
    build_suppression_store,
    seed_demo_iocs,
    seed_demo_rules,
)
from aisecops.L09_data_platform.alert_store import build_alert_store, seed_demo_alerts
from aisecops.L09_data_platform.event_store import build_event_store
from aisecops.L09_data_platform.report_store import build_report_store
from aisecops.L11_target_estate import (
    build_ai_asset_store,
    build_asset_store,
    seed_demo_ai_assets,
    seed_demo_assets,
)
from aisecops.L12_core_support.audit import build_audit_log
from aisecops.L12_core_support.config import Settings, get_settings
from aisecops.L12_core_support.config_store import build_config_store

STATIC = Path(__file__).parent / "static"


def apply_overrides(base: Settings, overrides: dict[str, str]) -> Settings:
    """把 DB 持久化的配置覆盖到 .env 基线上（按字段类型规整）。"""
    upd: dict[str, Any] = {}
    for k, v in overrides.items():
        if not hasattr(base, k):
            continue
        cur = getattr(base, k)
        if isinstance(cur, bool):
            upd[k] = str(v).lower() in ("1", "true", "yes", "on")
        elif isinstance(cur, float):
            try:
                upd[k] = float(v)
            except ValueError:
                pass
        else:
            upd[k] = v
    return base.model_copy(update=upd)


class Runtime:
    """平台运行时：持有所有层的实例。routers 经此读写共享状态。"""

    def __init__(self) -> None:
        db_url = get_settings().database_url
        self.db_url = db_url

        # 系统配置持久化（P-18）：DB 覆盖 .env；敏感键加密。先算"有效配置"再建网关。
        self.config_store = build_config_store(db_url)
        self.settings = apply_overrides(get_settings(), self.config_store.all_decrypted())

        # 场景→模型路由（§4.4）；注入网关
        self.route_store = build_route_store(db_url)
        seed_default_routes(self.route_store)
        self.gateway = build_gateway(self.settings)
        default_provider = next(
            (p.name for p in self.gateway.providers if not p.is_stub), self.gateway.providers[-1].name
        )
        self.gateway.router = ScenarioRouter(self.route_store.all(), default=default_provider)
        self.registry = build_tool_registry()

        # Agent 运行时配置（阈值/cross-check/启停，改了即时生效）；注入 ctx
        self.agent_configs = build_agent_config_store(db_url)
        seed_agent_configs(self.agent_configs)
        # 审计链落 PG（C-23 不可篡改 + P-18 重启不丢）；无 DB 回退内存
        self.audit = build_audit_log(db_url)

        # L03 知识库 + RAG（检索增强，C-7 Reranker 必备）；首启种案例，索引缺失则重建
        self.kb = build_knowledge_base(db_url)
        seed_demo_knowledge(self.kb)
        if self.kb.vectors.count() == 0 and self.kb.store.all():
            self.kb.reindex_all()

        self.ctx = AgentContext(
            llm=self.gateway,
            tools=self.registry,
            agent_configs=self.agent_configs,
            audit=self.audit,
            rag=self.kb,
        )

        # HITL 工单库；真威胁分诊会自动建单
        self.tickets = build_ticket_store(db_url)
        if not self.tickets.all():
            seed_demo_tickets(self.tickets)
        self.triage = build_alert_triage_service(self.ctx, self.tickets)
        self.invest = build_investigation_service(self.ctx)
        self.corr = build_correlation_service(self.ctx)

        # 告警库
        self.alerts = build_alert_store(db_url)
        if self.alerts.count() == 0:
            seed_demo_alerts(self.alerts)

        # 降噪（L08 前置）
        self.supp_rules = build_suppression_store(db_url)
        seed_demo_rules(self.supp_rules)
        self.dedup = DedupEngine(self.supp_rules)

        # 安全事件库（关联确认产物）
        self.events = build_event_store(db_url)

        # SOAR 处置剧本（L02 平台核心）
        self.playbooks = build_playbook_store(db_url)
        seed_demo_playbooks(self.playbooks)
        self.runs = build_run_store(db_url)

        # 通知中枢（L02 平台核心）
        self.channels = build_channel_store(db_url)
        self.dispatch_rules = build_dispatch_rule_store(db_url)
        self.records = build_record_store(db_url)
        seed_demo_channels_rules(self.channels, self.dispatch_rules, self.settings.wechat_webhook)
        self.notifier = build_notifier(self.settings.allow_outbound)

        # 报表中心（L07）
        self.reports = build_report_store(db_url)
        self.reporting = build_reporting_service(self.gateway)

        # 资产 CMDB（L11）
        self.assets = build_asset_store(db_url)
        if not self.assets.all():
            seed_demo_assets(self.assets)

        # AI 资产合规 / Shadow AI 治理（L11，C-3）
        self.ai_assets = build_ai_asset_store(db_url)
        seed_demo_ai_assets(self.ai_assets)

        # 威胁情报 IoC（L08）
        self.iocs = build_ioc_store(db_url)
        if not self.iocs.all():
            seed_demo_iocs(self.iocs)

        # 告警接入出口（L07）：归一化+情报+降噪+入库流水线，从表现层下沉（审查 #23）
        self.ingest = build_ingest_service(normalize_alert, self.iocs, self.dedup, self.alerts, self.supp_rules)

        # Prompt 治理（L04）
        self.prompts = build_prompt_store(db_url)
        seed_demo_prompts(self.prompts)

        # MCP 工具适配器（L06）
        self.adapters = build_adapter_store(db_url)
        if not self.adapters.all():
            seed_demo_adapters(self.adapters, self.settings.es_hosts)

        # 用户与 RBAC（L02 IAM）+ 会话令牌（写端点鉴权）
        self.users = build_user_store(db_url)
        seed_demo_users(self.users)
        self.sessions = SessionStore()


# 全局单例：所有 router 共享
rt = Runtime()


# ---- FastAPI 依赖（可被测试 dependency_overrides 覆盖）----
def get_gateway() -> LLMGateway:
    return rt.gateway


def get_triage_service() -> AlertTriageService:
    return rt.triage


def get_invest_service() -> InvestigationService:
    return rt.invest


def get_corr_service() -> CorrelationService:
    return rt.corr

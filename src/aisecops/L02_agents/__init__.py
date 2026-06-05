"""L02 · AI Agent 群 + 平台核心管控。

当前：Agent 基类 + Orchestrator + Triage Agent（Sprint 3 首切片）。
"""

from .agent_config import (
    AgentConfig,
    AgentConfigStore,
    InMemoryAgentConfigStore,
    PgAgentConfigStore,
    build_agent_config_store,
    resolve_cross_check,
    seed_agent_configs,
)
from .base import Agent, AgentContext, AgentResult, Task, sanitize_for_tag
from .correlation import CorrelationAgent, CorrelationConclusion
from .enrichment import EnrichmentAgent
from .intel import IntelAgent
from .reporter import ReporterAgent
from .responder import ResponderAgent
from .tuning import TuningAgent
from .investigation import InvestigationAgent, InvestigationVerdict
from .memory import InMemoryMemoryStore, MemoryStore
from .notify import (
    Channel,
    ChannelStore,
    DispatchRule,
    DispatchRuleStore,
    RecordStore,
    SendRecord,
    build_channel_store,
    build_dispatch_rule_store,
    build_record_store,
    mask_url,
    match_dispatch_rules,
    seed_demo_channels_rules,
)
from .orchestrator import Orchestrator, OrchestratorError
from .sessions import Principal, SessionStore
from .soar import (
    InMemoryPlaybookStore,
    InMemoryRunStore,
    PgPlaybookStore,
    PgRunStore,
    Playbook,
    PlaybookRun,
    PlaybookStore,
    RunStore,
    build_playbook_store,
    build_run_store,
    match_playbooks,
    seed_demo_playbooks,
)
from .tickets import (
    InMemoryTicketStore,
    PgTicketStore,
    Ticket,
    TicketError,
    TicketStore,
    build_ticket_store,
    seed_demo_tickets,
)
from .triage import TriageAgent, TriageVerdict
from .users import (
    InMemoryUserStore,
    PgUserStore,
    User,
    UserStore,
    build_user_store,
    seed_demo_users,
)

__all__ = [
    "Agent",
    "AgentContext",
    "AgentResult",
    "Task",
    "MemoryStore",
    "InMemoryMemoryStore",
    "Orchestrator",
    "OrchestratorError",
    "Principal",
    "SessionStore",
    "TriageAgent",
    "TriageVerdict",
    "InvestigationAgent",
    "InvestigationVerdict",
    "CorrelationAgent",
    "CorrelationConclusion",
    "EnrichmentAgent",
    "IntelAgent",
    "ResponderAgent",
    "ReporterAgent",
    "TuningAgent",
    "sanitize_for_tag",
    "AgentConfig",
    "AgentConfigStore",
    "InMemoryAgentConfigStore",
    "PgAgentConfigStore",
    "build_agent_config_store",
    "seed_agent_configs",
    "resolve_cross_check",
    "Playbook",
    "PlaybookRun",
    "PlaybookStore",
    "InMemoryPlaybookStore",
    "PgPlaybookStore",
    "RunStore",
    "InMemoryRunStore",
    "PgRunStore",
    "build_playbook_store",
    "build_run_store",
    "match_playbooks",
    "seed_demo_playbooks",
    "Channel",
    "ChannelStore",
    "DispatchRule",
    "DispatchRuleStore",
    "SendRecord",
    "RecordStore",
    "build_channel_store",
    "build_dispatch_rule_store",
    "build_record_store",
    "match_dispatch_rules",
    "mask_url",
    "seed_demo_channels_rules",
    "Ticket",
    "TicketStore",
    "InMemoryTicketStore",
    "PgTicketStore",
    "build_ticket_store",
    "TicketError",
    "seed_demo_tickets",
    "User",
    "UserStore",
    "InMemoryUserStore",
    "PgUserStore",
    "build_user_store",
    "seed_demo_users",
]

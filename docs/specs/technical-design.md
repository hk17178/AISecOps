# 技术设计方案 · AISECOPS（自用版）

- 版本：v0.2（自用重写）
- 状态：Draft
- 日期：2026-05-26
- 作者：muzi
- 关联：[PRD](PRD.md) · [V2 架构](../architecture-v2.md) · [CONSTRAINTS](../../CONSTRAINTS.md) · [ADR-0003 自用定位](../adr/0003-self-use-positioning.md)

---

## 1. 总体架构

**总体架构以 V2 文字版为准**：[`docs/architecture-v2.md`](../architecture-v2.md)

本文不重复架构图，只补充实现层面的设计与选型。

### 1.1 设计原则速查
- 分层即职责（C-13）
- LLM 必经 L05 Gateway（C-6）
- 外部工具必经 L06 MCP（P-3）
- HITL 默认（C-8）
- 抑制幻觉（C-24~C-27）
- 自用约束：成本控制 + 单人可维护

---

## 2. 部署形态（单一本地部署）

> 自用项目，**只做一种部署**：在你/你们公司环境跑。

### 2.1 部署目标环境（待确认）

| 维度 | 候选 | 决策时点 |
|---|---|---|
| 跑在哪 | 公司机房 / 公司云服务器 / 个人服务器 | Sprint 1 前 |
| OS | Rocky 9.4 / Ubuntu 22.04 / 24.04 | 看你们 IT 偏好 |
| 编排 | docker-compose（推荐起步）/ K8s（如已有 K8s 平台） | docker-compose 优先 |

### 2.2 拓扑（PoC 起步形态）

```
┌─────────────────────────────────────────────┐
│ 单节点（PoC / 初期）                          │
│                                              │
│  L01 UI (nginx) ── L02 FastAPI ── L05 Gateway│
│                       │              │       │
│                       └─ L06 MCP ────┘       │
│                                              │
│  数据层（同节点 docker-compose）              │
│   Postgres / ClickHouse / Kafka / Redis     │
│   MinIO / Milvus / Vault / Prometheus       │
│                                              │
│  外部依赖                                     │
│   - 客户内网 LLM 或 SaaS LLM API（自选）      │
│   - 你们现有的 SIEM/EDR（通过 MCP 接入）       │
└─────────────────────────────────────────────┘
```

### 2.3 演进路径
- **PoC 阶段**：单节点 all-in-one docker-compose
- **生产阶段**（若同事真用起来）：拆 2-3 节点（应用 + 数据 + 中间件）
- **远期**（不强求）：K8s 化、HA

---

## 3. 关键技术选型

每个组件给：**选型** / **备选** / **理由**。选型变更必须写 ADR。

### 3.1 主语言 + Web 框架

| 组件 | 选型 | 备选 | 理由 |
|---|---|---|---|
| 主语言 | **Python 3.11+** | Go / TypeScript | AI 生态最成熟 |
| Web 框架 | **FastAPI** | Flask | 异步 + Pydantic + OpenAPI 自动 |
| 包管理 | **uv** | poetry / pip | 最快 |
| Linter / Formatter | **ruff** | black + isort | 一个工具搞定 |
| 类型检查 | **mypy strict** | pyright | 业界标准 |

### 3.2 Agent / LLM / RAG

| 组件 | 选型 | 备选 | 理由 |
|---|---|---|---|
| Agent 编排 | **自研** | LangGraph / LangChain Agents | 自用规模小，自研更轻；LangGraph 太重 |
| LLM Gateway | **自研** | LiteLLM | 自用要做出域开关 / 成本控制 / stub，自研可控 |
| RAG 框架 | **LlamaIndex** | LangChain | Reranker 现成 |
| Reranker | **bge-reranker-v2-m3** | Cohere Rerank（成本） | 开源本地跑，不烧 token |
| Embedding | **bge-m3** | text-embedding-3-large（成本） | 中文好、本地 |
| 向量库 | **Milvus Lite**（PoC）→ **Milvus**（生产） | Qdrant / Weaviate | Lite 嵌入式，自用够 |
| 知识图谱 | 暂不上 | Neo4j（V2 再说） | 自用初期数据不够形成图 |

### 3.3 MCP 生态

| 组件 | 选型 |
|---|---|
| MCP SDK | Anthropic Python SDK |
| Server 框架 | 自研脚手架（`/add-mcp`） |
| **V1.0 实现 3 个起步** | Syslog（采集）+ 你们 SIEM/EDR 二选一（数据源）+ 通知（企微/钉钉/邮件 一种） |

### 3.4 数据层（自用规模 → 中间件起步配置）

| 组件 | 选型 | 起步部署 |
|---|---|---|
| 关系数据库 | **PostgreSQL 16** | docker 单实例 |
| 时序 / 日志 | **ClickHouse 24.x LTS** | docker 单实例 |
| 消息中间件 | **Redis Streams**（起步）→ Kafka（如吞吐撑不住） | Redis 单实例 |
| 对象存储 | **MinIO** | docker 单实例 |
| 全文检索 | **暂不上**（PG 全文索引够用） | - |
| 流处理 | **暂不上**（数据量不大，Python 批处理就够） | - |

> 自用规模，**Kafka / OpenSearch / Flink 起步全不上**，等数据量真撑不住再加。

### 3.5 L05 LLM Gateway 设计

```python
# 模块结构
src/aisecops/L05_gateway/llm_gateway/
├── __init__.py
├── gateway.py          # 主入口
├── routing.py          # 多 provider 路由
├── budget.py           # ⭐ 自用关键：Token 预算控制 + 月度上限
├── desensitize.py      # 出域脱敏（C-32）
├── outbound_switch.py  # 出域开关（默认关）
├── fallback.py         # 降级链（C-34）
├── metadata.py         # 调用 metadata（C-33）
├── stub.py             # Stub 模式（C-18）
└── providers/
    ├── doubao.py       # 默认 SaaS 选项
    ├── tongyi.py
    ├── zhipu.py
    ├── openai_compat.py  # 通用 OpenAI-compat（接本地 vLLM/Ollama）
    └── claude.py        # 出域开关开启才用
```

**核心 API**：
```python
async def call(
    prompt: str | list[Message],
    *,
    scenario: str,              # 必填，如 "L07/alert_triage"
    response_model: Type[BaseModel] | None = None,  # C-21 schema 校验
    temperature: float = 0,     # C-30 默认 0
    seed: int | None = None,
    max_tokens: int = 4096,
    cross_check: bool = False,  # C-27 高风险动作启用
    allow_outbound: bool = False,  # C-32 出域开关
    budget_tag: str = "default", # ⭐ 自用：用于成本分摊
) -> LLMResponse:
    """L05 Gateway 统一调用入口。所有 LLM 调用必经此。"""
```

### 3.6 L02 Agent 接口

```python
class Agent(ABC):
    name: str
    role: str  # orchestrator / triage / investigation / responder / reporter
    
    @abstractmethod
    async def run(self, task: Task, ctx: AgentContext) -> AgentResult:
        """执行任务，返回结构化结果。
        
        ctx 注入：
        - memory_store: L02 Memory
        - llm: L05 Gateway 实例
        - mcp_registry: L06 MCP 注册表
        - audit: L12 审计日志
        """
        ...
```

### 3.7 部署技术栈

| 维度 | 选型 | 最低版本 |
|---|---|---|
| 容器 | Docker | 24.0+ |
| 编排 | **docker-compose**（起步）/ K8s（如需） | v2.20+ / 1.28+ |
| 配置 | Pydantic Settings + .env | - |
| 凭证 | Vault | 1.16+ |
| 可观测 | OpenTelemetry + Loki + Prometheus + Grafana | OTel 0.105+ |
| CI / CD | GitHub Actions | - |

完整版本：见 [compatibility.md](compatibility.md)。

**自用关键约束**：
- 单节点 PoC 资源：**8 vCPU / 32 GB / 600 GB SSD** 即可
- **GPU 不在平台需求**，LLM 走 API
- 离线部署能力**可保留**（接本地 LLM 就不需要外网）

---

## 4. 内部接口设计（自用简版）

### 4.1 接口形态
- **L01 ↔ L02**：HTTP（FastAPI 自动 OpenAPI）
- **L02 Agent 间通信**：内存 Queue（PoC）→ Redis Streams（生产）
- **L02 ↔ L05/L06**：函数调用（同进程）
- **MCP**：JSON-RPC over stdio / HTTP（官方协议）

### 4.2 内部 RBAC（3 角色简版）

| 角色 | 能做 | 不能做 |
|---|---|---|
| 管理员 | 全部 + 配置 + HITL 审批 + 查所有 | - |
| 分析师 | 看告警 / 调查 / 标注 / Chat | 配置 / HITL 审批高风险 |
| 普通查看 | 看仪表盘 / 自己关注的告警 | 操作 |

实现：FastAPI 依赖注入 + 简单的角色装饰器。**不做** OAuth / SSO 复杂集成（用 LDAP 或公司 IDP 简单对接即可）。

---

## 5. 数据流（自用 PoC 路径）

### 5.1 告警分诊路径

```
你们 SIEM/EDR ─── webhook ────► FastAPI /webhook/alert (L01)
                                    ↓
                            Redis Streams: alerts.raw
                                    ↓
                  L09 Python 批处理：归一化 + 入 ClickHouse
                                    ↓
              定时扫描 / 实时触发 → L08 关联分析
                                    ↓
                       高风险 → L02 Triage Agent
                       ├─ L03 RAG 查相似历史
                       ├─ L04 LLM 经 L05 Gateway
                       └─ L06 MCP 富化（IP / IoC / CMDB）
                                    ↓
                         结构化结果落 ClickHouse
                                    ↓
                高置信度 + 写操作 → HITL Channel
                                    ↓
                    L01 工单 UI → 你 / 同事审批
```

### 5.2 反馈飞轮（V2 架构必备，但自用简化版）

```
L01 标注（确认/否决/修正）→ Redis Streams: analyst.feedback
                                   ↓
                           L02 Tuning Agent（周扫一次）
                                   ↓
            写 feedback store（ClickHouse）→ 用于：
              ① 调 Prompt（人工 + AI 协同迭代）
              ② **不训 DSLM**（自用数据量不够，V3+ 再说）
              ③ 调阈值（置信度 / abstain 触发线）
```

---

## 6. 关键决策（链接 ADR）

| 决策 | ADR |
|---|---|
| 12 层架构 | [ADR-0001](../adr/0001-architecture-baseline.md) |
| V2 取代 V1 PNG | [ADR-0002](../adr/0002-architecture-v2-supersedes-png.md) |
| 自建自用定位 | [ADR-0003](../adr/0003-self-use-positioning.md) |
| 主语言 Python | 待补 ADR-0004 |
| Agent 编排自研 | 待补 ADR-0005 |
| 数据中间件起步 Redis Streams | 待补 ADR-0006 |

---

## 7. 演进路径（务实版）

### 7.1 PoC → 团队上线
- 单节点 docker-compose
- 同事真用起来 → 加 RBAC + 数据备份

### 7.2 团队上线 → 数据撑不住
- 数据节点单拆（ClickHouse 独立）
- Kafka 替换 Redis Streams（如吞吐 > 1K EPS）

### 7.3 远期可能（不强求）
- K8s 化
- HA / 灾备
- DSLM 训练（**前提**：累积了 5000+ 标注样本）
- 多团队隔离（如果公司其他部门也想用）

### 7.4 假如未来想商业化
按 [ADR-0003](../adr/0003-self-use-positioning.md) 后续动作补：
- 多租户（行级隔离 / Schema 级）
- 合规对照矩阵
- 双部署模式（加回 SaaS）
- 客户文档体系

**预计增量 3-6 个月**。12 层架构本身不需要推翻。

---

## 8. 待决策事项

按 PRD §9 的 5 条决策（跑在哪 / 数据源 / LLM / 通知 / CMDB），在 Sprint 1 启动前明确，每条进一份 ADR。

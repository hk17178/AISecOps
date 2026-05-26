# 技术设计方案 · AISECOPS

- 版本：v0.1
- 状态：Draft（骨架阶段）
- 日期：2026-05-26
- 作者：muzi
- 关联：[PRD](PRD.md) · [V2 架构](../architecture-v2.md) · [CONSTRAINTS](../../CONSTRAINTS.md)

---

## 1. 总体架构

**总体架构以 V2 文字版为准**：[`docs/architecture-v2.md`](../architecture-v2.md)

本文不再重复架构图，只补充**实现层面的设计**。

### 1.1 设计原则速查
- 分层即职责（CONSTRAINTS C-13）
- LLM 必经 L05 Gateway（C-6）
- 外部工具必经 L06 MCP（PRINCIPLES P-3）
- 多模型混合（C-4：LLM + DSLM + ML + 统计 + 静态分析）
- HITL 默认（C-8）
- 反馈飞轮设计（P-10）

---

## 2. 双部署模式设计

PRD §2.1 定义了 SaaS / 本地双模式。技术层面共有 **80% 核心 + 20% 差异**。

### 2.1 共有核心（不分模式）
- 全部 L01 ~ L12 代码本身
- 12 层分层 / 跨层隔离
- MCP 协议 + 7+1 Agent 架构
- 配置驱动差异（不重写代码）

### 2.2 差异点

| 维度 | SaaS 模式 | 本地模式 |
|---|---|---|
| **LLM 默认** | 豆包 + Claude（云 API） | Qwen / DeepSeek 本地化部署（vLLM） |
| **数据存储** | ClickHouse Cloud / 阿里云 OSS | 客户自建 ClickHouse + MinIO |
| **多租户** | 必须（行级隔离 + IAM） | 单租户简化 |
| **运维** | 我方托管 K8s | 客户自维护 docker-compose / K8s |
| **更新** | 自动滚动 | 客户手动升级（季度版本） |
| **合规级别** | ISO 27001 + 等保 2.0 二级 | 等保 2.0 三级 + 个保法 + 数安法 |
| **数据出域** | 默认本地区域内 | 物理隔离，完全不出域 |
| **License** | 订阅制（按用量） | 永久 License + 年维 |

### 2.3 架构差异图
```
SaaS 模式:
┌──────────────────────────────────┐
│ 客户 1 │ 客户 2 │ ... │ 客户 N   │  ← 多租户行级隔离
├──────────────────────────────────┤
│       L01-L12 共享核心            │
├──────────────────────────────────┤
│ 我方托管: K8s + ClickHouse Cloud │
│           + 阿里云 OSS           │
└──────────────────────────────────┘

本地模式:
┌──────────────────────────────────┐
│       L01-L12 完整栈              │
├──────────────────────────────────┤
│ 客户机房: K8s/docker-compose      │
│  + 客户 ClickHouse + MinIO        │
│  + 客户 Vault                     │
│  + 本地 vLLM (Qwen/DeepSeek)      │
└──────────────────────────────────┘
```

---

## 3. 关键技术选型

每个组件给：**选型** / **备选** / **理由**。所有选型变更必须写 ADR。

### 3.1 主语言 + Web 框架

| 组件 | 选型 | 备选 | 理由 |
|---|---|---|---|
| 主语言 | Python 3.11+ | Go / TypeScript | AI 生态最成熟（LangChain/LlamaIndex/MCP SDK） |
| Web 框架 | FastAPI | Flask / Django | 异步原生、Pydantic 集成、OpenAPI 自动生成 |
| 异步运行时 | asyncio + uvloop | trio | 主流，生态完善 |
| 包管理 | uv | poetry / pip | 最快，2025 起业界主流 |
| Linter / Formatter | ruff | black + isort + flake8 | 一个工具搞定，已在 hooks 配置 |
| 类型检查 | mypy strict | pyright | 业界标准 |

### 3.2 Agent / LLM / RAG

| 组件 | 选型 | 备选 | 理由 |
|---|---|---|---|
| Agent 编排 | **自研 + LangGraph 借鉴** | LangChain Agents / CrewAI / AutoGen | LangGraph 太重；自研可控、对齐 V2 架构 |
| LLM Gateway (L05) | **自研** + 借鉴 LiteLLM | LiteLLM 直接用 | 自研便于做出域开关、metadata、降级链（C-32/33/34） |
| RAG 框架 | **LlamaIndex** | LangChain / Haystack | RAG 专精，Reranker 现成 |
| Reranker | bge-reranker-v2-m3 | Cohere Rerank | 开源、可本地化（C-32 数据不出域） |
| Embedding | bge-m3 | text-embedding-3-large | 中文好、可本地 |
| 向量库 | **Milvus** | Qdrant / Weaviate | 国产、商业化成熟、Milvus Lite 内嵌可用 |
| 知识图谱 | **Neo4j** | NebulaGraph | 生态成熟；Nebula 留 P2 替换备选 |

### 3.3 MCP 生态

| 组件 | 选型 |
|---|---|
| MCP SDK | Anthropic Python SDK |
| MCP 协议版本 | 跟随官方最新稳定 |
| Server 框架 | 自研脚手架（`/add-mcp` 命令）|

### 3.4 数据中台

| 组件 | 选型 | 备选 | 理由 |
|---|---|---|---|
| 消息中间件 | **Kafka** | Pulsar / Redis Streams | 业界事实标准 |
| 时序数据库 | **ClickHouse** | TimescaleDB / Doris | 安全日志典型场景，性能优势 |
| 对象存储 | **MinIO**（本地）/ OSS（SaaS） | S3 | 双部署天然适配 |
| 全文检索 | **OpenSearch** | Elasticsearch | 开源，免授权风险 |
| 流处理 | Flink | Spark Streaming | 状态化处理优势 |
| 数据湖 | Iceberg | Hudi / Delta | 三选一中最开源 |

### 3.5 L05 LLM Gateway 详细设计

```python
# 模块结构
src/aisecops/L05_gateway/llm_gateway/
├── __init__.py
├── gateway.py          # 主入口
├── routing.py          # 多 provider 路由
├── budget.py           # Token 预算 + 计费
├── desensitize.py      # 出域脱敏（C-32）
├── outbound_switch.py  # 出域开关
├── fallback.py         # 降级链（C-34）
├── metadata.py         # 调用 metadata（C-33）
├── stub.py             # Stub 模式（C-18）
└── providers/
    ├── doubao.py
    ├── tongyi.py
    ├── zhipu.py
    ├── claude.py
    └── openai.py
```

**关键 API**：
```python
async def call(
    prompt: str | list[Message],
    *,
    scenario: str,           # 必填，如 "L07/alert_triage"
    response_model: Type[BaseModel] | None = None,  # C-21 schema 校验
    temperature: float = 0,  # C-30 默认 0
    seed: int | None = None,
    max_tokens: int = 4096,
    cross_check: bool = False,  # C-27 高风险动作启用
    allow_outbound: bool = False,  # C-32 出域开关
) -> LLMResponse:
    """L05 Gateway 统一调用入口。所有 LLM 调用必经此。"""
```

### 3.6 L02 Agent 设计

```python
# 每个 Agent 标准接口
class Agent(ABC):
    name: str
    role: str  # orchestrator / triage / ...
    
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

**Orchestrator 调度模式**：基于任务 DAG 而非自由对话。所有跨 Agent 通信走结构化消息（C-21 + PRINCIPLES P-8）。

### 3.7 部署技术栈

| 维度 | 选型 |
|---|---|
| 容器化 | Docker + BuildKit |
| 编排 | docker-compose（本地）+ K8s（生产/SaaS） |
| 服务发现 | K8s Service / Consul（备选） |
| 配置管理 | Pydantic Settings + envfile |
| 凭证 | HashiCorp Vault（本地 / SaaS）+ 阿里云 KMS（SaaS 备选） |
| 可观测 | OpenTelemetry + Tempo（trace）+ Loki（log）+ Prometheus（metric） |
| 监控告警 | Grafana + Alertmanager |
| CI / CD | GitHub Actions + ArgoCD（生产） |

---

## 4. 接口设计

### 4.1 内部接口
- **HTTP**：L01 ↔ L02 用 OpenAPI（FastAPI 自动生成）
- **Agent 间通信**：内存 Queue（单进程）或 Kafka（分布式）；消息 schema 走 Pydantic
- **MCP**：JSON-RPC over stdio / HTTP（MCP 官方协议）

### 4.2 对外 API
- 主要 OpenAPI（生成在 `/openapi.json`）
- 详细 endpoint 设计待 P0 阶段补充（设计原则：RESTful + 资源化）

### 4.3 Webhook
- 入：Prometheus / Zabbix / 各 SIEM 告警 webhook
- 出：邮件 / 企微 / 钉钉 / 自定义 webhook

---

## 5. 数据流（实现层面）

V2 架构文档画了**逻辑数据流**，本节补充**实现层的数据流**：

### 5.1 告警分诊路径（典型）
```
SIEM Webhook → FastAPI /webhook/alert (L01)
            → Kafka topic: alerts.raw (L10)
            → Flink Job: alert-normalize (L09)
            → ClickHouse: alerts (L09)
            → L08 correlation (定时扫描 / Kafka 触发)
            → 高风险告警 → Kafka topic: triage.pending
            → L02 Triage Agent 消费
              → L03 RAG 查相似历史
              → L04 LLM 推理 (经 L05 Gateway)
              → L06 MCP 富化 (IP 归属 / IoC 关联)
              → 结构化结果落 ClickHouse: triage.results
            → 若高置信度 + 写操作 → L02 Responder + HITL Channel
            → L01 工单 UI 通知
```

### 5.2 反馈飞轮路径（V2 新增）
```
L01 工单决策（分析师"确认/否决/修正"）
  → Kafka topic: analyst.feedback
  → L02 Tuning Agent 消费
  → 写入 feedback store (ClickHouse)
  → 周期任务（每周）从 feedback store 生成训练样本
  → 触发 L04 DSLM fine-tune pipeline
  → 新版 DSLM shadow mode 评估（PRINCIPLES P-11）
  → 通过 → 切流量
```

---

## 6. 关键决策（链接 ADR）

| 决策 | ADR |
|---|---|
| 采用 12 层架构 | [ADR-0001](../adr/0001-architecture-baseline.md) |
| V2 文字版取代 V1 PNG | [ADR-0002](../adr/0002-architecture-v2-supersedes-png.md) |
| 主语言 Python | 待补 ADR-0003 |
| Agent 编排自研 vs LangGraph | 待补 ADR-0004 |
| 数据中台选型 | 待补 ADR-0005 |
| 向量库选型 Milvus | 待补 ADR-0006 |

---

## 7. 演进路径

### 7.1 单体 → 微服务
**V1.0：单 Python 进程 + Kafka 解耦** 即可。
**V2.0（客户超 100 家或 EPS > 100K 时）**：按层拆服务：
- L05 Gateway 独立服务（横切）
- L06 MCP 各自独立服务
- L02 Agent Worker 池
- L08 算法引擎独立服务（资源密集）

### 7.2 单实例 → 多区域
SaaS 模式 V2.0 起支持多区域部署，按客户数据所在地路由。

### 7.3 国内 → 出海（如有）
- LLM 切 Claude / Gemini
- 合规切 SOC2 + GDPR
- UI 国际化

---

## 8. 待决策事项

- [ ] **ADR-0003**：主语言为何选 Python（vs Go）—— 性能 trade-off 需正式记录
- [ ] **ADR-0004**：Agent 编排框架（自研 vs LangGraph vs CrewAI）—— 需 PoC 比较
- [ ] **ADR-0005**：数据中台选型（ClickHouse vs StarRocks vs Doris）
- [ ] **ADR-0006**：向量库（Milvus vs Qdrant）
- [ ] **HITL Channel 实现**：is 独立 UI 队列还是嵌入工单系统？
- [ ] **多租户隔离粒度**：行级 / Schema 级 / 物理级？
- [ ] **DSLM 训练管道**：自建 vs 用阿里云 PAI / 腾讯云 TI？

每条待 P0 阶段启动前明确。

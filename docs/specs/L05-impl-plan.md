# L05 LLM Gateway 实现计划（Sprint 2）

- 版本：v0.1
- 状态：Draft
- 日期：2026-06-03
- 作者：muzi（+ AI 辅助）
- 方法：计划先行 + 测试先行（TDD）
- 关联：[技术设计 §3.5](technical-design.md) · [开发计划 Sprint 2](dev-plan.md) · [CONSTRAINTS](../../CONSTRAINTS.md) · [ADR-0008 跨层 DAG](../adr/0008-cross-layer-dependency-dag.md)

---

## 1. 目标与范围

**一句话**：所有 LLM 调用收敛到一个 `await gateway.call(...)`，自带成本控制 / 脱敏 / 出域开关 / stub / 降级。

**边界**：本 Sprint 只做 Gateway 本体 + 1 个 SaaS provider + 1 个本地 provider。不碰 Agent、不碰数据库（**纯 Python，stub-first，无需 Docker**）。

**跨层定位**（ADR-0008）：L05 是横切例外层，任何层都可经它调 LLM；它自身只依赖 L12（凭证/可观测），不反向依赖业务层。

## 2. 下手前要锁的 3 个决策

| 决策 | 建议默认（可改） | 影响 |
|---|---|---|
| 第一个 SaaS provider | **先不接真的**，用 stub + `openai_compat`（指向 Ollama 本地）跑通 | 真 key 等 PRD §9 定了再插 |
| HTTP 客户端 | `httpx`（异步） | 加一条 dep |
| 重试/超时 | `tenacity` + httpx timeout | 加一条 dep |

> 关键取舍：**先 stub 后真 provider**——整个 Gateway 在没有任何 API key、没有 Docker 的情况下可被 100% 测到（满足 C-18 + Sprint 2 DoD「stub 模式 pytest 通过」）。

## 3. 模块结构（= technical-design §3.5）

```
src/aisecops/L05_gateway/llm_gateway/
├── __init__.py
├── gateway.py          # 主入口 call()
├── routing.py          # 多 provider 路由
├── budget.py           # ⭐ Token 预算控制 + 月度上限
├── desensitize.py      # 出域脱敏（C-32）
├── outbound_switch.py  # 出域开关（默认关）
├── fallback.py         # 降级链（C-34）
├── metadata.py         # 调用 metadata（C-33）
├── stub.py             # Stub 模式（C-18）
├── models.py           # Message / LLMRequest / LLMResponse / CallMetadata
└── providers/
    ├── base.py         # Provider 抽象
    ├── stub.py         # StubProvider（确定性假响应）
    ├── openai_compat.py# 通用 OpenAI-compat（接本地 vLLM/Ollama）
    ├── doubao.py / tongyi.py / zhipu.py  # SaaS（按需）
    └── claude.py       # 出域开关开启才用
```

## 4. 构建顺序（每步：先写测试 → 再实现 → 跑绿）

> **进度（2026-06-04）**：**S0–S6 ✅ 已实现 + 测试**（10 测试，make check + CI 全绿）。S7–S12 待续。

| # | 步骤 | 先写的测试 | 满足铁律 |
|---|---|---|---|
| **S0** | 包骨架 + 加 deps（httpx/tenacity/pydantic） | `test_import` | — |
| **S1** | 数据契约：`Message`/`LLMRequest`/`LLMResponse`/`CallMetadata` | schema 校验、必填项 | C-21 地基 |
| **S2** | Provider 抽象 + **StubProvider** | stub 返回可复现 | **C-18** |
| **S3** | `gateway.call()` happy path → 路由到 stub，打通 `temperature=0/seed` | 一行调用成功、seed 透传 | **C-30** |
| **S4** | `metadata.py`：每次调用产出 metadata（token/scenario/budget_tag/延迟/model） | 每次调用必有 metadata | **C-33** |
| **S5** | `budget.py`：月度上限 + 逐次记账 + 超预算→降级/告警（注入假时钟） | 超预算触发降级 | 自用关键 |
| **S6** | `fallback.py`：主模型→备模型→stub→报错 | 每级降级路径 | **C-34** |
| **S7** | `outbound_switch.py` + `desensitize.py`：出域默认**关**；开启才脱敏后发 | 默认拦截出域、PII 被打码 | **C-32/C-20** |
| **S8** | `response_model` 校验：LLM 输出对 Pydantic 不符则重试/abstain | 不符触发重试 | **C-21** |
| **S9** | `cross_check`：高风险双模型一致性 | 两 stub 一致/冲突 | **C-27** |
| **S10** | 真 providers：`openai_compat`(Ollama) + 1 个 SaaS（集成测试打 marker，CI 跳过） | 集成测试（本地手跑） | C-6 |
| **S11** | 成本指标出口（Prometheus metric / 简单查询） | 月成本可读 | Sprint 2 DoD |
| **S12** | 覆盖率 ≥80% + 中文 docstring + `layer-architect` 自审 | `pytest --cov` | C-28 / DoD |

> S0–S9 全部可在 stub 下离线跑绿；S10 才需要真 LLM（可延后）。关键路径：**S1→S2→S3→S4**，四步后"一行 call + 可观测 + 可复现"立住。

## 5. 核心 API 契约（= technical-design §3.5，不变）

```python
async def call(
    prompt: str | list[Message],
    *,
    scenario: str,                                   # 必填，如 "L07/alert_triage"
    response_model: Type[BaseModel] | None = None,   # C-21 schema 校验
    temperature: float = 0,                          # C-30 默认 0
    seed: int | None = None,
    max_tokens: int = 4096,
    cross_check: bool = False,                        # C-27 高风险启用
    allow_outbound: bool = False,                     # C-32 出域开关
    budget_tag: str = "default",                     # 成本分摊
) -> LLMResponse: ...
```

## 6. 测试策略

- **stub-first**：默认所有单测走 StubProvider，`pytest` 不联网、不烧 token、CI 全绿。
- 集成测试用 `@pytest.mark.integration` 标记，本地手跑接 Ollama，CI `-m "not integration"` 跳过。
- 假时钟测 budget（不依赖真实时间），假 provider 测 fallback / cross_check。

## 7. 风险 & 待决策

- **R1**：真 SaaS provider 选哪个（豆包/通义/智谱）→ 不阻塞 S0–S9，等定。
- **R2**：`cross_check` 双模型翻倍 token → 默认只给高风险开，记进 budget 成本模型。
- **R3**：Gateway 自研 vs LiteLLM 选型建议补一篇 ADR（候选 ADR-0009）。

## 8. DoD（= dev-plan Sprint 2）

- [ ] 业务一行 `await gateway.call(...)` 完成
- [ ] Stub 模式 pytest 通过
- [ ] 月度成本可见
- [ ] 出域开关验证生效
- [ ] 单测覆盖 ≥ 80%（核心模块）

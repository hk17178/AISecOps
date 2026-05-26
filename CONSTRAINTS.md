# CONSTRAINTS.md · 项目铁律

> **违反就要回滚的硬约束**。软原则在 [PRINCIPLES.md](PRINCIPLES.md)。

## 🔴 一、AISecOps 名实必须相符

### C-1. SEC > OPS
L07 业务能力出口**必须**至少覆盖以下 6 个安全场景中的 4 个：
- 告警分诊（alert_triage）
- 事件调查（investigation）
- 威胁狩猎（threat_hunting）
- SOAR 处置（soar_playbooks）
- UEBA
- 漏洞 / 合规（vuln_compliance）

❌ **反例**：把 L07 填成"容量预测 + 性能基线 + 主机巡检" → 这就是 AIOps 了，违反命名

### C-2. 安全分析必须有
L08 智能分析引擎**必须**包含安全侧算法（不能只有 AIOps 算法）：
- 攻击图（attack_graph）—— 至少一个图算法实现
- Kill Chain 还原（kill_chain）
- IoC 关联（ioc_correlation）
- UEBA 算法（ueba_analytics）

❌ **反例**：L08 只有异常检测和容量预测 → 退回

### C-3. AI 模型合规对象必须建模
L11 `target_estate/ai_compliance/` 必须有实质内容（不能只是占位）。
2026 业界基线把 Shadow AI 治理纳入 AISecOps。

## 🔴 二、AI 架构必须够格

### C-4. 不能纯 LLM
任何 P1 及以上的 SecOps 场景**禁止**只用 LLM 兜底，必须组合：
- LLM + DSLM
- LLM + ML / 统计
- LLM + 图算法
- LLM + 静态规则

❌ **反例**：告警分诊就是把告警贴给 LLM 让它说"是真是假" → 不通过 PR

### C-5. Multi-Agent 必须有 Orchestrator
L02 `orchestrator/` 必须实现且必须经 Orchestrator 调度其他 Agent。

❌ **反例**：9 个扁平 Agent 自行互相调用（itops-agent-platform 模式）→ 回滚

### C-6. LLM 调用必须经 L05 Gateway
任何代码层（L01 ~ L12）**不许**直接 `import openai` / `import anthropic`，必须：
```python
from aisecops.L05_gateway.llm_gateway import LLMClient
```

❌ **反例**：L02 某 Agent 直连 `openai.ChatCompletion.create()` → 重构

### C-7. Reranker 必须有
L03 RAG 流水线**必须**含 Reranker（业界 SOTA 基线）。
缺 Reranker 的 RAG 直接退回。

## 🔴 三、安全与治理

### C-8. HITL 默认开启
任何"写"操作类工具（隔离主机 / 禁用账号 / 封 IP / 删数据 / 修改配置）：
- 必须先入 L02 工单引擎
- 必须有人审节点
- 不允许 Agent 直接执行

❌ **反例**：Responder Agent 自动封了一个生产 IP → 严重事故

### C-9. 凭证零硬编码
任何外部系统凭证（API key / 密码 / token）：
- 必须走 `L12_core_support/secrets/`
- 代码里只允许 `get_secret("KEY_NAME")` 这种引用
- `.env` / `secrets/` / `credentials/` 在 .gitignore 兜底

### C-10. 模型权重不入库
DSLM / Embedding 模型权重文件（.bin / .safetensors / .gguf / .pt / .onnx）：
- 必须走对象存储或 HuggingFace Hub
- .gitignore 已挡，**不要绕过**

### C-11. 原始安全数据不入库
任何采集来的日志、告警、流量 PCAP：
- 不许进 git
- 测试 fixture 必须用合成数据（fake）

## 🔴 四、数据层不能"玩具化"

### C-12. SQLite 仅用于本地开发与测试
**禁止**在生产路径上用 SQLite 兜底数据中台。L09 数据中台正式实现必须用：
- 消息：Kafka / Pulsar / Redis Streams（任选）
- 存储：ClickHouse / Postgres / 对象存储
- 索引：ES / OpenSearch

❌ **反例**：itops-agent-platform 单 SQLite 39 张表跑全平台 → 反例典型

### C-13. 跨层调用禁止
- 不许跨层 import（如 L07 直接 import L10）
- 不许反向调用（如 L09 调 L07）
- 例外只能是 L05 Gateway / L06 MCP / L12 横切支撑

新建跨层例外必须写 ADR。

## 🔴 五、工程纪律

### C-14. 中文优先
- 代码注释、docstring、README、commit message 一律中文
- 函数 / 类 / 变量名英文 snake_case / PascalCase

### C-15. 视觉权威是架构图
设计冲突时一律以 `docs/architecture.png` 为准。
要改架构 → 先改 PNG（或写 ADR 说明 PNG 已过时）→ 再改代码。

### C-16. Commit 风格
- 用总结短语，不用数字编号
- 主题不同就拆 commit
- 严禁 `--no-verify` / `--force` 跳过钩子

### C-17. Test 不 mock 外部安全工具
集成测试**禁止** mock 真实安全工具的响应（沿用 EHR 项目教训）：
- mock 通过 ≠ 真接通
- 用 stub mode 或 testcontainers，不要 unittest.mock 一整个 SIEM

### C-18. L05 LLM Gateway 必须支持 stub
否则每次 pytest 都烧真 token。

---

## 违反铁律的处理流程

1. CI / 主对话发现违规 → **拒绝合并**
2. 已合并发现 → **回滚提交**
3. 设计阶段发现 → 找 `security-analyst` 或 `layer-architect` 评审

## 铁律的修改

修改本文件需要写 ADR 说明理由，并在 commit message 注明 `BREAKING: 修订 C-X`。

# PRINCIPLES.md · 设计原则

> **指导设计选择的软原则**。比 [CONSTRAINTS.md](CONSTRAINTS.md) 灵活，但反对要给理由。

## 一、分层与边界

### P-1. 分层即职责
12 层不是文件分类，是**职责边界**。任何代码先回答"我在哪一层"，再回答"我做什么"。

### P-2. 接口窄而稳，实现可以肥
- 跨层接口要小、要稳：`Agent.run(task) -> Result`
- 实现内部可以复杂，外面不要看见
- 这是 [[layer-architect]] 守门的依据

## 二、AI 工程

### P-3. MCP 优先于硬编码集成
新接入外部工具时：
- 先问：有没有 MCP？官方 / 社区？
- 没有 → 自己写一个 MCP（L06/custom）
- 不要把工具调用硬编码进 L02 / L07

理由：业界 2026 战场是 MCP 生态，硬编码集成是一次性投入。

### P-4. DSLM 不是 LLM 的备胎，是主力
对垂直任务（日志分类、恶意载荷、误报抑制）：
- 优先训 / 用 DSLM（开源 + fine-tune）
- LLM 用于推理、归纳、报告生成
- 不要把所有事都丢给 LLM

理由：成本、延迟、可解释性、合规。

### P-5. RAG 不是万金油
- 知识更新频繁 → RAG
- 需要精确数值 → 工具调用（MCP）
- 需要推理链 → 多步 Agent
- 安全 IoC 这种**结构化**数据 → 数据库 + 检索，不是 RAG

### P-6. Prompt 治理从 Day 1 开始
- Prompt 必须版本化（git）
- 上线前 A/B 比较
- 生产 Prompt 改动要走 PR，不许直接改代码字符串

## 三、Agent 协作

### P-7. Orchestrator 是协调，不是大脑
- Orchestrator 只做任务分解、路由、聚合
- 不做业务推理
- 业务在专职 Agent 里（Triage / Investigation / ...）

### P-8. Agent 间通信用结构化消息
- 不要 Agent A 把自然语言扔给 Agent B
- 用 JSON Schema 定义消息格式
- Memory Store 存的是结构化状态

### P-9. HITL 默认，自动化是例外
- 任何"写"动作默认要人审
- 自动化必须是**显式**开启（Playbook 配置）
- 自动化必须有"撤销"路径

## 四、数据飞轮

### P-10. 反馈即资产
- 分析师每一次"确认 / 否决 / 修正"都要落库
- Tuning Agent 周期性消费反馈，回流 DSLM 训练
- 没有飞轮的 AISecOps 是一锤子买卖

### P-11. 影子模式（Shadow Mode）评估新模型
新 Prompt / 新 DSLM 上线前：
- 先 shadow 跑 1-2 周（只观察不动）
- 对比生产模型差异
- 通过才切流量

## 五、运维与运营

### P-12. 零运维优先
- 能用托管 / Serverless 不用自维护
- 用户硬性偏好 [[feedback-chinese-zero-ops]]
- 例外要写 ADR

### P-13. 可观测性内建
- 所有 Agent 调用、LLM 调用、MCP 调用都有 trace
- L12 observability 横切所有层
- 日志结构化（JSON），不要 print 半句中文半句英文

### P-14. 成本意识
- L05 Gateway 必须能给出每个 Agent / 每个场景的 token 消耗
- Reranker 用便宜模型
- 不要给所有事都用 Opus / GPT-4 Turbo

## 六、风格与文化

### P-15. 简洁 > 全面
- README 200 行以内能讲清楚就不要 500 行
- 注释只写"为什么"，不写"做了什么"
- 三处相似代码再抽象

### P-16. 业界对标作为决策依据
- 不确定怎么做 → 看 Microsoft / CrowdStrike / 奇安信 / 启明 怎么做
- 不抄实现，抄思路
- 写 README 必须有"业界对标"段

### P-17. 不要科技风
- 用户硬性偏好：朴素、克制、信息密度
- 不要"赋能 / 重塑 / 全栈 / 一站式"这种营销话术
- 文档不要堆 emoji（路径标记除外）

---

## 原则之间冲突时

- P-3 MCP 优先 vs P-12 零运维 → 零运维优先（先用第三方 SaaS MCP）
- P-4 DSLM 主力 vs P-12 零运维 → P-4 优先（DSLM 是核心竞争力）
- P-9 HITL vs 用户体验 → P-9 必赢（这是铁律 C-8 的软版本）

## 怎么修订本文件

软原则修订门槛低于铁律：
- 在 PR 说明里给"为什么修"
- 写一个简短 ADR 即可
- 不需要 BREAKING 标签

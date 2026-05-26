# Architecture Decision Records (ADR)

记录项目重要架构决策的"为什么"。每个 ADR 一个文件，文件名 `NNNN-<slug>.md`。

## 格式

```markdown
# ADR-NNNN · <标题>

- 状态：Proposed / Accepted / Deprecated / Superseded by ADR-XXXX
- 日期：YYYY-MM-DD
- 决策者：<姓名>

## 背景
为什么要做这个决策？当时面临什么问题？

## 决策
我们决定怎么做？

## 后果
正面：...
负面：...
风险：...

## 备选方案（如有）
我们考虑过什么、为什么没选？
```

## 何时写 ADR

见 [layer-architect](../../.claude/agents/layer-architect.md) 中的触发条件。简化版：
- 跨层调用例外
- 选型决策（库、协议、数据库）
- 引入新层 / 删除层 / 合并层
- 修订 CONSTRAINTS.md 铁律
- 引入新数据库 / MQ / 协议

## 索引

| 编号 | 标题 | 状态 |
|---|---|---|
| [0001](0001-architecture-baseline.md) | 采用 12 层架构作为 AISecOps 基线 | Accepted |
| [0002](0002-architecture-v2-supersedes-png.md) | 架构 V2 取代 V1 PNG 成为视觉权威 | Accepted |

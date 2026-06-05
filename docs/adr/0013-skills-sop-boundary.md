# ADR-0013 · Skills(SOP) 的定位与边界

- 状态：已接受
- 日期：2026-06-05
- 相关：architecture-v2 §L04（Skills 库）· [架构补齐计划 Phase 3](../specs/architecture-gap-plan.md)

## 背景

architecture-v2 的 L04 列了 **Skills(SOP)**，但一直零代码。要建它，先得厘清它和已有的
SOAR Playbook(L02)、Prompt(L04)、知识库(L03) 的边界——否则四者职责重叠、各做一半。

## 决策

**Skill = 结构化的标准操作流程（SOP）：一组有序步骤 + 适用条件 + 引用，给 Agent/分析师当
"怎么做某类事"的指引与 checklist；本身不自动执行。** 落 L04（知识资产，与 Prompt 并列）。

### 四者边界（一句话各自是什么）

| 概念 | 层 | 是什么 | 自动执行? | 形态 |
|---|---|---|---|---|
| **Skill(SOP)** | L04 | "怎么做某类事"的标准步骤清单 + 适用条件 | 否（指引/checklist） | 结构化(steps) |
| **SOAR Playbook** | L02 | "自动做处置"：触发→动作序列，经 HITL | 是（经人审） | 结构化(actions) |
| **Prompt** | L04 | LLM 人设/指引文本 | —（喂模型） | 文本 |
| **知识库** | L03 | 过往经验/手册等非结构化文档 | 否（RAG 检索） | 非结构化文本 |

记忆法：**Skill 教"按步骤怎么查/怎么处置"（人或 Agent 照着做）；Playbook 是"自动替你做处置"；
Prompt 是"模型的人设"；知识库是"读过的资料"。**

### 落地

- L04 `SkillStore`（仓储 PG/内存，与其它 store 一致）：Skill {name, category, scenario, steps, refs, enabled, version}。
- `match_skills(context_text, skills)`：按场景关键词匹配适用 SOP（确定性）。
- 接入：经 `ctx.skills` 注入；**Investigation Agent 调查时附上匹配到的 SOP 步骤**（给分析师可照做的
  checklist，C-25 用既有 SOP 而非让模型现编流程）。Responder 后续可引用处置 SOP。
- L01「Skills · SOP」管理页：CRUD（鉴权+审计+持久化）。

## 后果
- 正面：补齐 V2 L04 Skills；四概念边界清晰，不再重叠；调查给出可照做的标准步骤。
- 负面：又多一类资产要维护（但与 Playbook/知识库各司其职，不冗余）。

## 关联
- architecture-v2 §L04 · [ADR-0011](0011-l01-composition-root-and-routers.md) · CONSTRAINTS C-25（tool/SOP 优先于记忆）

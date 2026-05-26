# ADR-0002 · 架构 V2 取代 V1 PNG 成为视觉权威

- 状态：Accepted
- 日期：2026-05-26
- 决策者：muzi

## 背景

ADR-0001 采用 12 层架构图（`docs/architecture.png`）作为视觉权威。在编写 CONSTRAINTS.md / PRINCIPLES.md 过程中，对照业界 2026 AISecOps 基线（Microsoft Security Copilot / CrowdStrike Charlotte / 奇安信 QAX-GPT），发现 V1 PNG 存在 **5 大结构性缺口 + 3 处小毛病**：

### 5 大结构性缺口
1. **L7 标签错位**：图中写"AIOps Capabilities × 用户价值场景"，**不是 SecOps Capabilities**。一个叫 AISecOps 的项目却在业务出口层叫 AIOps，名实不符。
2. **L8 算法层缺安全半边**：图中列了 anomaly_detection / root_cause / capacity_prediction / performance_baseline（全是 AIOps 算法），**没有** attack_graph / kill_chain / ioc_correlation / ueba_analytics / compromise_judgment 等业界 AISecOps 基线必备的安全分析算法。
3. **L4 缺 DSLM**：图中只标"大模型 LLM"，没有领域小模型框。业界共识"LLM + DSLM + ML + 统计 + 静态分析"五件套，DSLM 是 Charlotte / QAX-GPT 的核心壁垒。
4. **L2 缺 SOAR Playbook 引擎**：图中只有"工单引擎"（人工流转），没有自动化处置剧本引擎。SOAR Playbook 与工单引擎是两回事。
5. **缺反馈飞轮**：图中无 L1 工单/报表 → L2 Tuning Agent → L4 模型再训练的数据回流箭头。没有飞轮就是一锤子买卖。

### 3 处小毛病
6. **L3 / L4 命名重叠**：两层都叫"AI 资产层"，内容上 L3 偏 RAG 流水线、L4 偏模型与知识本体，但图上不直观。
7. **L12 内容模糊**：图中写"资产标识/资产识别/调度集群"，"资产标识"和"资产识别"重复，且缺凭证管理、可观测性等横切支撑。
8. **HITL 通道隐藏**：图中没显式画出"人审节点"在哪里，与 CONSTRAINTS C-8 "HITL 默认开启"矛盾。

### 紧迫性
当前仓库已经出现**权威冲突**：CONSTRAINTS.md 多条铁律（C-2 / C-4 / P-10 等）已经要求图里没有的东西。如果坚持"PNG 是权威"，CONSTRAINTS 就越界；如果按 CONSTRAINTS 走，PNG 就过时。必须解决。

## 决策

**采用"路径 A"**：
- 新建 [`docs/architecture-v2.md`](../architecture-v2.md) 作为文字版权威架构文档，补齐 8 个缺口。
- V1 PNG（`docs/architecture.png`）状态置为 **Superseded by V2**，保留作历史参考，**不再用于新设计**。
- 更新 CONSTRAINTS C-15「视觉权威是架构图」改指 V2 文字版。
- 更新 CLAUDE.md / `.claude/context/architecture.md` 等引用，指向 V2。
- 用户后续按 V2 重画 V2 PNG；新 PNG 完成后，与 V2 文字版互为参考（图直观、文字精确）。

## 后果

**正面**：
- 解决权威冲突，CONSTRAINTS 与架构图重新对齐
- V2 是文字版，**可 Git 版本控、可 PR 评审、可随代码进化**——比 PNG 强很多
- 8 个缺口全部显式补上，新人看 V2 不会再"按 V1 设计→违反 CONSTRAINTS"
- ASCII 图保留视觉锚点，不至于完全失去"一图看全"的能力

**负面**：
- 需要用户后续重画 V2 PNG（一次性工作量）
- 文字版 + ASCII 图的"一图看全"体验不如真 PNG
- 短期内出现"V1 PNG 在仓库里但已过时"的混淆——靠 V2 文档头部警示 + 本 ADR 缓解

**风险**：
- 如果 V2 PNG 长期不画，V1 PNG 残留在 docs/ 可能造成新人误读 → **缓解**：V2 文档头部已强标红"V1 已 superseded"
- V2 文字版后续也可能过时 → 通过 CI / PR 评审 + ADR 修订流程兜底

## 备选方案

### 备选 1：路径 B —— 直接生成 Mermaid 图当主视图
- 用 Mermaid 画 12 层图，直接当主架构
- **拒绝理由**：12 层信息密度太高，Mermaid 表现力不如手绘 PNG；ASCII + 文字组合在 markdown 里展示更稳

### 备选 2：路径 C —— 只写 ADR 记录偏差，不改架构图
- PNG 继续当权威，ADR 列出已知偏差
- **拒绝理由**：权威冲突不解决，长期会让 CONSTRAINTS 失去严肃性；只是把问题拖延

### 备选 3：用户直接重画 PNG，跳过 V2 文字版
- **拒绝理由**：用户重画需要明确的"差什么"清单，V2 文字版正好提供这个清单；并且文字版本身就有独立价值（可版本控、可 review）

## 后续行动

- [ ] 用户按 V2 文字版重画 V2 PNG（替换 `docs/architecture.png` 或新建 `docs/architecture-v2.png`）
- [ ] V2 PNG 完成后更新本 ADR 状态为"Completed"
- [ ] 删除或归档 V1 PNG 到 `docs/_archive/` 目录（可选）

## 关联

- [ADR-0001 12 层架构基线](0001-architecture-baseline.md)
- [架构 V2 文字版](../architecture-v2.md)
- [CONSTRAINTS.md C-2 / C-4 / C-15](../../CONSTRAINTS.md)
- [PRINCIPLES.md P-10 反馈即资产](../../PRINCIPLES.md)

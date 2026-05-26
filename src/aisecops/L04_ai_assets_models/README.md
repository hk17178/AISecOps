# L04 · AI 资产层 — 模型与知识本体 (Models & Knowledge)

## 职责
平台的"原料库"——大模型、领域小模型、Prompt、Skills(SOP)、知识图谱。L03 RAG 流水线消费这一层。

## 子组件
- **llm/** —— 大模型统一抽象（与 L05 LLM Gateway 配合）
- **dslm/** —— **领域小模型 (Domain-Specific LM)**，业界基线必备
  - 日志分类 DSLM
  - 恶意载荷识别 DSLM
  - 误报抑制 DSLM
- **skills_sop/** —— Skills 库（含 SOP 标准作业程序）
- **prompts/** —— Prompt 模板库（版本化，纳入 L02 prompt_governance）
- **memory/** —— 嵌入式 Memory（与 L02 memory_store 区别：本层是结构定义）
- **knowledge_graph/** —— 资产关系、攻击者画像、TTP 知识图谱

## 业界对标
- CrowdStrike Charlotte 训练自 Falcon Complete MDR 百万决策（DSLM 飞轮）
- 启明星辰 AIDK 智能体框架
- 360 安全大模型

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

## 为什么 DSLM 是必须的
业界共识："**LLM + DSLM + ML + 统计 + 静态分析**" 多模型混合是 AISecOps 的灵魂。纯 LLM 兜底是公认的反模式：成本高、可解释差、领域准确率不达标。

# L08 · 智能分析引擎 (Analytics Engines)

## 职责
传统 ML / 统计 / 图算法引擎层。**非 LLM 算法的家**——业界共识"LLM 之外的另一半"。

## 子组件（AIOps + SecOps 双半边）

### 通用分析（AIOps 侧）
- **anomaly_detection/** —— 异常检测
- **correlation/** —— 关联分析
- **root_cause/** —— 根因分析
- **clustering/** —— 聚类
- **capacity_prediction/** —— 容量预测
- **performance_baseline/** —— 性能基线
- **knowledge_extraction/** —— 知识抽取

### 🔑 安全分析（SecOps 侧 —— 业界基线必备）
- **attack_graph/** —— 攻击图重建
- **kill_chain/** —— Kill Chain 还原
- **ioc_correlation/** —— IoC 关联
- **ueba_analytics/** —— UEBA 算法核心
- **compromise_judgment/** —— 失陷研判

## 业界对标
- 阿里云安全中心：图计算 + 安全大模型自动溯源
- 绿盟 ISOP UEBA
- 安恒 AiLPHA XSIAM

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

## 为什么不能只靠 LLM
"安全分析半边"是 AISecOps 的灵魂。攻击图、Kill Chain、UEBA 这些都需要专用算法（图算法、序列模型、统计基线），LLM 不能替代——这也是 itops-agent-platform 那种"纯 LLM"方案永远成不了 AISecOps 的根本原因。

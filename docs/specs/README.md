# docs/specs/ · 核心设计文档

> 本目录是项目核心设计文档的家。**写代码前必读**。

## 当前文档

| 文档 | 作用 | 状态 |
|---|---|---|
| [PRD.md](PRD.md) | 需求文档：愿景 / 用户 / 场景 / 功能 / 非功能 / 成功指标 | Draft v0.1 |
| [technical-design.md](technical-design.md) | 技术设计：架构落地 / 技术选型 / 接口 / 部署 | Draft v0.1 |
| [dev-plan.md](dev-plan.md) | 开发计划：阶段 / Sprint / DoD / 风险 | Draft v0.1 |
| [compatibility.md](compatibility.md) | **系统兼容性矩阵**：OS / CPU / 容器 / K8s / 离线部署（硬性承诺） | Accepted v0.1 |

## 待补（按优先级）

- **数据模型设计** —— Agent Memory schema / 审计日志 / 事件 schema / DSLM 样本格式
- **API 设计** —— L01↔L02 接口 / 对外 OpenAPI / MCP 协议规范扩展
- **测试策略** —— 单测 / 集成测 / eval set 流程 / 安全测试 / CI 集成
- **AI 治理流程** —— Prompt 上线流程 / Model 切换 / HITL 审批层级 / 数据出域审批
- **威胁建模** —— STRIDE / ATT&CK，平台自身受到的威胁
- **合规对照** —— 等保 2.0 / 个保法 / 数安法 矩阵
- **运维手册** —— 部署 / 监控 / 故障处置

## 维护节奏
- PRD / 技术设计：**每季度 review**，重大变更升 v0.X → v1.X
- 开发计划：**每 Sprint 末 review**
- ADR 是不可变历史；本目录文档是活的

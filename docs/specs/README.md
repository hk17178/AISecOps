# docs/specs/ · 核心设计文档

> 本目录是项目核心设计文档的家。**写代码前必读**。

## 当前文档（v0.2 自用重写后，参见 [ADR-0003](../adr/0003-self-use-positioning.md)）

| 文档 | 作用 | 状态 |
|---|---|---|
| [PRD.md](PRD.md) | 需求文档（自用版）：3 角色 / 4 场景 / 务实指标 | Draft v0.2 |
| [technical-design.md](technical-design.md) | 技术设计（自用版）：单一本地部署 / 务实选型 | Draft v0.2 |
| [dev-plan.md](dev-plan.md) | 开发计划（自用版）：8 Sprint / 16 周到同事用起来 | Draft v0.2 |
| [compatibility.md](compatibility.md) | 系统兼容性矩阵：OS / CPU / 容器 / K8s / 端口 / 硬件 | Accepted v0.1 |

## 待补（自用优先级）

立刻补（Sprint 1 启动前）：
- **数据 schema 设计** —— 告警 / 事件 / IoC / Agent Memory / 审计日志 schema
- **测试与 eval 策略** —— eval set 怎么建 / 指标 / 安全测试方法（自用精简版）

按需补：
- **API 设计** —— 内部 API（够用就好，不做对外 OpenAPI 完整规范）
- **restart-guide.md** —— 自用关键，让 3 个月后的自己能快速重新上手
- **威胁建模**（自用简版）—— OWASP LLM Top 10 + MITRE ATLAS 思路指导，不做正式 STRIDE
- **运维手册**（自用简版）—— 部署 / 备份 / 故障排查（同事帮忙时需要）

不做（除非定位改变）：
- ~~合规对照矩阵（等保 / ISO / SOC2）~~
- ~~AI 治理流程（NIST AI RMF 系统化）~~
- ~~客户文档体系~~

## 维护节奏
- PRD / 技术设计：**每季度 review**，重大变更升 v0.X → v1.X
- 开发计划：**每 Sprint 末 review**
- ADR 是不可变历史；本目录文档是活的

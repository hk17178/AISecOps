# ADR-0005 · 主语言采用 Python 3.11+

- 状态：Accepted
- 日期：2026-06-04
- 决策者：muzi
- 来源：正式化 [technical-design §3.1](../specs/technical-design.md) 已定选型

## 背景

平台横跨 LLM/Agent/RAG/数据/Web，需要一门主语言统一技术栈、降低单人维护成本。候选：Python / Go / TypeScript。

## 决策

**主语言 = Python 3.11+。**

- AI 生态最成熟（LLM SDK、LlamaIndex、MCP SDK、数据科学栈）。
- 3.11+ 的异步性能与类型提示满足需要。
- 工具链统一：**uv**（包管理）+ **ruff**（lint/format）+ **mypy strict**（类型）+ **pytest**（测试）。
- Web 框架 FastAPI（异步 + Pydantic + 自动 OpenAPI）。

性能敏感的局部（如个别算法）后续可用 Rust/C 扩展或独立服务补，不改主语言。

## 后果

**正面**：生态红利最大、单人可维护、AI 招聘/协作面广。
**负面**：CPU 密集场景需额外优化（自用规模可接受）。
**风险**：依赖体积大 → 用 uv 锁定 + Docker 多阶段缓解。

## 关联

- [technical-design §3.1](../specs/technical-design.md) · [CONSTRAINTS C-14 中文优先](../../CONSTRAINTS.md)

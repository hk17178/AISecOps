---
description: 在 L06 下一键生成工具适配器骨架。默认薄适配器；加 --full 才产完整 MCP Server。用法：/add-mcp <category> <name> [--full]
allowed-tools: Write, Read, Glob, Bash, PowerShell
---

调用 `mcp-builder` subagent 完成以下任务：

**参数**：`$ARGUMENTS`
- 第一个词是分类（security_tools / data_sources / protocols / vendors / aiops / custom）
- 第二个词是工具名称（小写下划线）
- 可选 `--full`：生成完整 MCP Server；**不加则默认生成薄适配器**

**形态决策（[ADR-0004](../../docs/adr/0004-l06-mcp-optional-thin-adapter.md)）**：
- **默认 = 薄适配器**：自用单客户端下首选。一个 Python 函数 / CLI 封装，挂在 L06 统一注册表接口后。落地快、上下文干净。
- **`--full` = 完整 MCP Server**：仅当确有远程部署 / 授权握手 / MCP resources 需求时才用。
- 无论哪种形态，都**必须挂在 L06 注册表接口后**，走统一白名单 / 审计 / 凭证（不许 L02 直连）。

**任务（薄适配器，默认）**：
1. 在 `src/aisecops/L06_mcp_servers/<category>/<name>/` 下创建：
   - `__init__.py`
   - `adapter.py` —— 薄适配器：暴露注册表接口要求的函数（如 `list_tools()` / `call(tool, params)`），内部封装 SDK / CLI / API 调用
   - `README.md` —— 包含接入说明、tool 清单、凭证需求
   - `tests/test_<name>.py` —— stub mode 单测占位
2. `adapter.py` 给出可运行的最小实现（stub mode 下无需真凭证即可跑测试）

**任务（`--full`，加了才执行）**：
1. 改为在该目录下创建：
   - `__init__.py`
   - `server.py` —— MCP server 入口骨架（pip install mcp 后能起来）
   - `tools.py` —— tool 定义占位
   - `resources.py` —— resource 占位
   - `README.md` / `tests/test_<name>.py` —— 同上
2. README 顶部注明"完整 MCP Server 形态，理由：<远程/授权握手/resources>"

**两种形态都要：README 必须列出**：
   - 这个 MCP 接哪个系统
   - 暴露的 tool 清单（先列 1-2 个占位）
   - 凭证名（**必须走 L12 secrets，不能硬编码**）
   - 业界对标：类似的产品/连接器
4. 最后用一段总结告诉用户：
   - 文件路径
   - 下一步要做什么（实现 tool / 配置凭证 / 写测试）

**铁律提醒**：
- 写操作类 tool 必须打 `dangerous: true`
- 任何外部凭证不能写在代码里

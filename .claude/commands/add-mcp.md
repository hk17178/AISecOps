---
description: 在 L06 下一键生成 MCP Server 骨架。用法：/add-mcp <category> <name>，如 /add-mcp security_tools splunk
allowed-tools: Write, Read, Glob, Bash, PowerShell
---

调用 `mcp-builder` subagent 完成以下任务：

**参数**：`$ARGUMENTS`
- 第一个词是分类（security_tools / data_sources / protocols / vendors / aiops / custom）
- 第二个词是 MCP 名称（小写下划线）

**任务**：
1. 在 `src/aisecops/L06_mcp_servers/<category>/<name>/` 下创建：
   - `__init__.py`
   - `server.py` —— MCP server 入口骨架
   - `tools.py` —— tool 定义占位
   - `resources.py` —— resource 占位
   - `README.md` —— 包含接入说明、tool 清单、凭证需求
   - `tests/test_<name>.py` —— stub mode 单测占位
2. 在 `server.py` 中放可运行的最小 MCP server（pip install mcp 后能起来）
3. README 必须列出：
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

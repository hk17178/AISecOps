---
description: 检查某一层文件完整度与跨层合规。用法：/verify-layer L0X（如 /verify-layer L06）
allowed-tools: Read, Glob, Grep, Bash, PowerShell
---

**参数**：`$ARGUMENTS` —— 层号（L01 ~ L12）

调用 `layer-architect` subagent 完成检查：

## 检查清单

### 一、文件完整度
- [ ] `src/aisecops/<layer>/README.md` 存在
- [ ] `src/aisecops/<layer>/__init__.py` 存在
- [ ] README 包含：职责、子组件清单、业界对标、当前状态
- [ ] 已实现的子模块在 README 中有标注

### 二、跨层合规
扫描这一层所有 `.py` 文件，检查 import：
- [ ] 没有跨层 import（如 L07 直接 import L10）
- [ ] LLM 调用都经过 L05
- [ ] 外部工具调用都经过 L06

### 三、命名规范
- [ ] 文件 / 函数名遵守 Python snake_case
- [ ] 中文注释 / docstring
- [ ] 没有 itops-agent-platform 反模式叫法（如"9 个智能体"）

### 四、测试覆盖
- [ ] `tests/<layer>/` 镜像目录存在
- [ ] 已实现模块的测试覆盖率（如能跑 pytest --cov）
- [ ] L08 算法引擎模块覆盖率必须 ≥ 80%

### 五、安全约束
- [ ] 没有硬编码凭证（grep API_KEY / TOKEN / PASSWORD）
- [ ] 没有 print 敏感数据
- [ ] L02/L07 处置类动作都有 HITL 节点

## 输出格式
```
=== Layer L0X 验证报告 ===
完整度  : X / Y 项 (xx%)
合规性  : ✅ 通过 / 🔴 发现 N 处违规
测试    : 覆盖率 xx%
违规清单:
  1. ...
  2. ...
建议下一步:
  - ...
```

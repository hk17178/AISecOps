# L05 · 流量主干道 — LLM Gateway / API Gateway

## 职责
统一接入治理层。所有出向 LLM 调用、入向 API 调用都走本层，做认证、限流、计费、路由、日志、敏感数据脱敏。

## 子组件
- **llm_gateway/** —— LLM 统一接入
  - 多 Provider 路由（豆包 / OpenAI / Anthropic / Ollama / vLLM）
  - Token 计费与配额
  - 出向脱敏（防 Prompt 泄密）
  - Prompt 缓存命中率优化
- **api_gateway/** —— API 统一接入
  - 速率限制
  - 鉴权（与 L02 IAM 协同）
  - 审计日志

## 业界对标
- Microsoft Security Copilot 的统一 LLM 接入
- 启明星辰 1+1+N 的"统一大模型"层
- LiteLLM / Helicone（开源参考）

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

## 为什么必须独立成层
itops-agent-platform 这类直连 LLM API 的方案，无法做计费、脱敏、灰度——演进上限被锁死。Gateway 层是治理与生态扩展的基础设施。

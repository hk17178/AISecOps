# L10 · 数据采集层 (Data Collection)

## 职责
从被管对象（L11）采集原始 telemetry，是数据中台（L09）的入口。

## 子组件
- **agents/** —— 主机/容器 Agent（与 L02 AI Agent 同名不同义）
- **log/** —— 日志采集（Syslog / Fluent Bit / Filebeat）
- **trace/** —— 分布式追踪（OpenTelemetry）
- **metric/** —— 指标采集（Prometheus / Telegraf）
- **sensors/** —— 各类传感器（流量探针 / 蜜罐 / DLP）

## 业界对标
- Splunk Universal Forwarder / Heavy Forwarder
- Datadog Agent
- 阿里云 LogTail

## 当前状态
🟡 占位 —— 仅目录与本说明，未实现

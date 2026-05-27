# 系统兼容性矩阵 · AISECOPS

- 版本：v0.1
- 状态：Accepted（用户已拍板，本文件为权威）
- 日期：2026-05-26
- 关联：[PRD §5.8](PRD.md) · [技术设计 §3.7](technical-design.md)

> **本文件是系统兼容性的唯一权威**。
> 其他文档涉及"支持哪些环境"的描述一律以本文为准；如代码/测试发现某环境无法支持，**必须**先改本文（含 ADR）。

---

## 1. 一句话承诺

> AISECOPS 在 **x86_64 架构**上承诺支持：
> - **Rocky Linux / RHEL / AlmaLinux 9.4+**（同源 RPM 系）
> - **Ubuntu 22.04 LTS / 24.04 LTS**（Debian 系）
> - **SaaS 模式必须基于 K8s 1.28+**；**本地模式** K8s 与 docker-compose 二选一
> - **本地模式必须支持完全离线部署**

---

## 2. 操作系统兼容性矩阵

| OS 发行版 | 版本 | 是否支持 | 验证级别 | 备注 |
|---|---|---|---|---|
| **Rocky Linux** | **9.4+** | ✅ 必须 | Tier-1（每发布版本必测） | 主要本地部署目标 |
| **RHEL** | **9.4+** | ✅ 必须 | Tier-1 | 与 Rocky 同源 |
| **AlmaLinux** | **9.4+** | ✅ 必须 | Tier-1 | 与 Rocky 同源 |
| **Ubuntu LTS** | **22.04 / 24.04** | ✅ 必须 | Tier-1 | 互联网客户主流 |
| CentOS Stream 9 | - | 🟡 尽力 | Tier-2（不主动测） | 可能可用，不承诺 |
| openEuler | - | ❌ 不支持 | - | V1.0 不在范围 |
| 麒麟 / 统信 UOS | - | ❌ 不支持 | - | V1.0 不在范围（信创版本待 V2 评估） |
| Debian 12 | - | ❌ 不支持 | - | V1.0 不在范围 |
| Windows Server | - | ❌ 不支持 | - | 永不支持 |
| macOS | - | 🟡 仅开发 | - | 开发者本机用，**禁止生产** |

### Tier 定义
- **Tier-1**：每次发布前 CI 必跑、SRE 必演练、文档必覆盖
- **Tier-2**：可能可用，但不主动测试，客户问"行不行"答"自测"
- **❌ 不支持**：明确拒绝，写在售前合同里

### V1.0 不支持但 V2 评估
- openEuler 22.03 LTS（金融客户偏好）
- 麒麟 V10 / 统信 UOS V20（信创刚需）
- ARM64 / aarch64 架构（鲲鹏 / 飞腾）

---

## 3. CPU 架构

| 架构 | 是否支持 | 备注 |
|---|---|---|
| **x86_64 / amd64** | ✅ 必须 | 唯一支持架构 |
| ARM64 / aarch64 | ❌ V1.0 不支持 | 国产化 ARM 服务器（鲲鹏/飞腾）待 V2 |
| RISC-V | ❌ 永不支持 | - |

镜像构建：仅产出 `linux/amd64` 镜像，不做多架构 manifest。

---

## 4. 容器运行时

| 运行时 | 最低版本 | 是否支持 | 备注 |
|---|---|---|---|
| **Docker Engine** | **24.0+** | ✅ 必须 | docker-compose v2.20+ |
| **containerd** | **1.7+** | ✅ 必须 | K8s 默认运行时 |
| Podman | 4.0+ | 🟡 尽力 | 可能可用，不主动测 |
| CRI-O | - | ❌ V1.0 不测 | - |

---

## 5. Kubernetes（SaaS 必须 / 本地可选）

### 5.1 SaaS 模式
- **K8s 1.28+ 必须**（不支持更低版本）
- **测试基线**：K8s 1.28 / 1.30（最新两个 LTS）
- Helm 3.14+
- 推荐发行版：
  - **生产 SaaS**：阿里云 ACK / 腾讯云 TKE 1.28+
  - **PoC**：k3s / kind（仅 demo，不生产）

### 5.2 本地部署模式（二选一）

| 编排方案 | 适用客户 | 最低版本 |
|---|---|---|
| **K8s** | 中大型客户（已有 K8s 平台） | 1.28+ |
| **docker-compose** | 中小型客户（运维资源有限） | v2.20+ |

客户可自选，平台必须**同时支持**两种部署方式。

### 5.3 K8s 资源对象
- Helm Chart（主交付物）
- 必备 CRD：无（V1.0 不依赖外部 Operator）
- 必备 Operator：无
- 网络插件：Calico / Cilium 任意（不绑定）
- 存储：StorageClass with `ReadWriteOnce`（数据卷）+ `ReadWriteMany`（共享配置）

### 5.4 K8s 版本演进策略
- 每年跟进 K8s 新 LTS（如 1.32 LTS）
- 旧版本 EOL 后 6 个月内 drop
- 最多同时支持 **3 个** K8s 版本

---

## 6. 离线部署（本地模式必须）

> **范围澄清**：本节只覆盖**平台自身**的离线部署。**LLM 推理引擎不在平台范围**——见 §8 LLM 接入。

### 6.1 离线包要求
本地模式发布必须含：
- **完整镜像 tar 包**（平台组件 + 数据库 + 中间件镜像）
- **依赖镜像仓库**（Harbor 或 docker-distribution，可选预置）
- **离线 Helm Chart**（含所有依赖 Chart）
- **离线 RPM / DEB 仓库**（OS 层依赖，如 systemd 服务文件）

### 6.2 离线网络要求
- 客户机房**完全可断网**部署平台成功
- 平台运行期不依赖任何外部 DNS、CDN、NTP（NTP 客户自配）
- 升级通过 USB / 客户内网镜像仓库 / 客户跳板机

### 6.3 离线 vs SaaS 功能差异
- SaaS 可调云上海外 LLM（Claude / GPT）；离线模式默认关闭跨境
- SaaS 自动安全补丁；离线模式客户手动季度升级
- 其他功能完全等价

---

## 7. 软件依赖版本

### 7.1 核心运行时

| 组件 | 最低版本 | 推荐版本 | 备注 |
|---|---|---|---|
| Python | 3.11 | 3.12 | 性能改善显著 |
| Node.js（前端构建） | 20 LTS | 22 LTS | - |
| Go（如需） | 1.22 | 1.23 | 仅部分 MCP 用 |

### 7.2 数据库与中间件

| 组件 | 最低版本 | 推荐版本 |
|---|---|---|
| **PostgreSQL**（关系数据） | 16 | 16.4+ |
| **ClickHouse**（时序/日志） | 24.3 LTS | 24.8 LTS |
| **Kafka** | 3.7 | 3.8+ |
| **MinIO**（对象存储） | RELEASE.2024-09 | RELEASE.2025-xx |
| **Milvus**（向量库） | 2.4 | 2.5+ |
| **Neo4j**（知识图谱） | 5.20 LTS | 5.22 LTS |
| **OpenSearch**（全文检索） | 2.15 | 2.17+ |
| **Redis** | 7.2 | 7.4 |

### 7.3 Web 与代理

| 组件 | 最低版本 |
|---|---|
| nginx | 1.24 |
| HAProxy（备选） | 2.8 |

### 7.4 凭证与可观测

| 组件 | 最低版本 |
|---|---|
| HashiCorp Vault | 1.16 |
| OpenTelemetry Collector | 0.105+ |
| Prometheus | 2.55 |
| Grafana | 11.x |

---

## 8. LLM 接入

> ⚠️ **重要边界澄清**
> AISECOPS 平台是 **LLM 的消费者**，**不是 LLM 推理引擎**。
> LLM 推理的部署、GPU、模型权重、显存优化**都不在本平台范围**，由客户或 LLM 服务方负责。
> 平台只通过两种标准方式接入 LLM。

### 8.1 平台接入 LLM 的两种方式

| 类型 | 接入方式 | 适用场景 |
|---|---|---|
| **本地部署模型** | OpenAI-compatible HTTP API（`base_url` + `api_key` 可选） | 客户自有 LLM 推理服务（vLLM / Ollama / Triton / 客户私有云 LLM） |
| **SaaS 模型** | 各厂商 API（HTTP + API key） | 豆包 / 通义 / 智谱 / Claude / OpenAI / Gemini 等公有 LLM |

### 8.2 平台对 LLM Provider 的硬性要求
- **必须支持**：OpenAI ChatCompletion 协议兼容接口（业界事实标准）
- **必须支持**：API key 或同等鉴权
- **推荐支持**：function calling / tool use 协议（用于 L02 Agent）
- **推荐支持**：JSON mode / structured output（用于 C-21 schema 校验）
- **可选支持**：流式输出（streaming）

### 8.3 平台 V1.0 验证过的 Provider

| Provider | 类型 | base_url 示例 | 验证级别 |
|---|---|---|---|
| **vLLM**（OpenAI-compatible） | 本地 | `http://<客户内网>:8000/v1` | ✅ Tier-1 |
| **Ollama** | 本地 | `http://<客户内网>:11434/v1` | ✅ Tier-1 |
| **豆包**（火山方舟） | SaaS | `https://ark.cn-beijing.volces.com/api/v3` | ✅ Tier-1 |
| **通义**（阿里灵积 DashScope） | SaaS | `https://dashscope.aliyuncs.com/compatible-mode/v1` | ✅ Tier-1 |
| **智谱**（BigModel） | SaaS | `https://open.bigmodel.cn/api/paas/v4` | ✅ Tier-1 |
| **Claude**（Anthropic） | SaaS | `https://api.anthropic.com` | 🟡 Tier-2（需出域开关） |
| **OpenAI** | SaaS | `https://api.openai.com/v1` | 🟡 Tier-2（需出域开关） |
| 其他 OpenAI-compatible | 本地/SaaS | 自定义 | 🟢 客户自测，平台尽力支持 |

### 8.4 客户责任 vs 平台责任

| 维度 | 客户 / LLM 服务方负责 | AISECOPS 平台负责 |
|---|---|---|
| LLM 推理引擎选型（vLLM/Ollama/Triton/SGLang） | ✅ | ❌ |
| GPU 硬件（A800/H800/昇腾/...） | ✅ | ❌ |
| 模型权重下载 / 量化 | ✅ | ❌ |
| LLM 服务高可用 / 弹性 | ✅ | ❌ |
| LLM 调用方式 / 多 Provider 路由 | ❌ | ✅（L05 Gateway） |
| Token 计费 / 限流 / 降级 | ❌ | ✅（L05 Gateway） |
| Prompt 治理 / 数据脱敏 | ❌ | ✅（L02 + L05） |

---

## 9. 网络端口清单

> 客户在防火墙 / 安全组上需要放通的端口清单。**默认建议 K8s 内部通信走 ClusterIP，仅暴露必要的对外端口**。

### 9.1 对外（用户访问平台）

| 端口 | 协议 | 用途 | 是否必须 |
|---|---|---|---|
| **443** | HTTPS | 平台 Web UI / 对外 API（L01/L02） | ✅ 必须 |
| 80 | HTTP | 强制跳转到 443（可选） | 🟡 推荐 |

### 9.2 入向（采集端接入）

| 端口 | 协议 | 用途 | 是否必须 |
|---|---|---|---|
| **514** | UDP/TCP | Syslog 采集（L10） | ✅ 接 Syslog 必须 |
| **5044** | TCP | Filebeat / Logstash | 🟡 接 Filebeat 必须 |
| **8443** | HTTPS | Webhook 接收（Prometheus / SIEM / 防火墙告警） | ✅ 必须 |
| 4317 / 4318 | gRPC / HTTP | OpenTelemetry 接收（L10） | 🟡 接 OTel 必须 |

### 9.3 出向（平台调外部）

| 目标 | 端口 | 协议 | 用途 | 是否默认放通 |
|---|---|---|---|---|
| 客户内网 LLM（vLLM/Ollama） | 自定 | HTTPS / HTTP | L05 LLM Gateway 调本地 LLM | ✅ 本地模式必须 |
| 火山方舟 / 阿里灵积 / 智谱 | 443 | HTTPS | SaaS LLM API | 🟡 启用 SaaS LLM 时 |
| Anthropic / OpenAI | 443 | HTTPS | 海外 LLM | ❌ **默认拒绝**（需出域开关 C-32） |
| 客户 SIEM/EDR/防火墙 API | 自定 | HTTPS / 各协议 | L06 MCP 调外部 | ✅ 按客户配 |
| 威胁情报源（VirusTotal/微步） | 443 | HTTPS | L06 TI MCP | 🟡 启用 TI 时 |
| Docker Registry / Harbor | 443 / 5000 | HTTPS | 镜像拉取（仅升级时） | ✅ SaaS / 在线升级 |
| 客户 SMTP / 企微 / 钉钉 | 25/465/587/443 | SMTP / HTTPS | 通知中枢 | 🟡 启用通知时 |

### 9.4 内部组件端口（仅平台内部 / K8s ClusterIP）

| 组件 | 端口 | 协议 |
|---|---|---|
| FastAPI 主服务（L02） | 8000 | HTTP |
| L05 LLM Gateway | 8005 | HTTP |
| L06 MCP Server 群 | 8060 起 | HTTP / stdio |
| PostgreSQL | 5432 | TCP |
| ClickHouse | 8123 / 9000 | HTTP / Native |
| Kafka | 9092 | TCP |
| Zookeeper（如用） | 2181 | TCP |
| Redis | 6379 | TCP |
| MinIO | 9000 / 9001 | HTTP（API / Console） |
| Milvus | 19530 / 9091 | gRPC / HTTP |
| Neo4j | 7474 / 7687 | HTTP / Bolt |
| OpenSearch | 9200 / 9300 | HTTP / TCP |
| Vault | 8200 | HTTPS |
| Prometheus | 9090 | HTTP |
| Grafana | 3000 | HTTP |
| Tempo / Loki | 3100 / 3200 | HTTP |

> 内部端口**不暴露给外部用户**，仅 K8s 集群内 / docker-compose network 内通信。

---

## 10. 平台自身硬件最低配置

> **不含 LLM 推理 GPU**（LLM 推理硬件见 §8 客户责任）。
> 本节只描述平台业务进程 + 数据中台 + 中间件所需资源。

### 10.1 单节点 PoC / 演示环境（all-in-one）

| 资源 | 最低 | 推荐 |
|---|---|---|
| CPU | 8 vCPU | 16 vCPU |
| RAM | 32 GB | 64 GB |
| 系统盘 | 100 GB SSD | 200 GB SSD |
| 数据盘 | 500 GB SSD | 1 TB NVMe |
| 网络 | 千兆 | 千兆 + 双网卡 |

### 10.2 生产小型（≤ 10K EPS）

| 角色 | 数量 | CPU | RAM | 磁盘 |
|---|---|---|---|---|
| 平台服务节点（L01/L02/L05） | 2 | 8 vCPU | 32 GB | 100 GB SSD |
| 数据节点（L09 ClickHouse + MinIO） | 3 | 16 vCPU | 64 GB | 4 TB NVMe |
| 中间件节点（Kafka + Redis + Vault） | 3 | 8 vCPU | 32 GB | 500 GB SSD |
| 算法节点（L08） | 2 | 16 vCPU | 64 GB | 200 GB SSD |

### 10.3 生产中型（10K-50K EPS）
按 §10.2 比例 × 2-3，详见 dev-plan 后续容量规划专项。

### 10.4 资源边界
- **GPU 不在平台需求**，平台进程纯 CPU 运行
- **LLM Gateway 的 RAM 占用**：与 Prompt 缓存大小相关，每 GB 缓存 ≈ 1 GB RAM
- **ClickHouse 磁盘**：按 EPS × 平均日志大小 × 保留周期估算（典型 30 天 1 TB / 万 EPS）

---

## 11. 浏览器（前端）

| 浏览器 | 最低版本 | 备注 |
|---|---|---|
| **Chrome / Edge / 360 极速** | 最近 2 个 stable | 主测 |
| **Firefox** | 最近 2 个 ESR | 主测 |
| Safari | 17+ | 兼容性测试 |
| IE / 旧 Edge | - | ❌ 永不支持 |

前端打包目标：ES2022。

---

## 12. 验证与测试矩阵

| 环境 | CI 验证 | 发布前演练 |
|---|---|---|
| Rocky 9.4 + K8s 1.28（本地） | ✅ | ✅ |
| Rocky 9.4 + docker-compose（本地） | ✅ | ✅ |
| RHEL 9.4 + K8s 1.30（SaaS） | ✅ | ✅ |
| Ubuntu 22.04 + K8s 1.28 | ✅ | ✅ |
| Ubuntu 24.04 + K8s 1.30 | ✅ | ✅ |
| AlmaLinux 9.4 + docker-compose | 🟡 抽测 | ✅ |
| Ubuntu 24.04 + docker-compose | 🟡 抽测 | ✅ |

CI 至少覆盖 5 个组合，发布前 SRE 实机演练 7 个组合。

---

## 13. 客户兼容性承诺书（售前模板）

> AISECOPS V1.0 在以下环境**承诺可部署、可正常运行、提供原厂支持**：
> - 操作系统：Rocky Linux 9.4+ / RHEL 9.4+ / AlmaLinux 9.4+ / Ubuntu 22.04 LTS / Ubuntu 24.04 LTS
> - CPU：x86_64
> - 编排：K8s 1.28+ （SaaS 模式必须 / 本地模式可选）或 docker-compose v2.20+（本地模式可选）
> - 容器：Docker 24+ 或 containerd 1.7+
> - 本地模式支持完全离线部署（平台自身）
> - LLM 接入：本地 OpenAI-compatible API 或 SaaS LLM API key

> **客户自备**：LLM 推理服务（vLLM/Ollama/客户私有云 LLM 或 SaaS LLM 订阅）及其 GPU 硬件。

> 以下环境**不在 V1.0 范围**：openEuler、麒麟、UOS、ARM64、Windows、macOS（生产）。

---

## 14. 变更流程

修订本文件必须：
1. 写 ADR 说明理由（如新增 OS 支持 / drop 旧版本）
2. 售前同步（兼容性承诺书更新）
3. CI 测试矩阵同步更新
4. dev-plan 同步（如新增 OS 需排 Sprint 验证）

# AISecOps 平台架构评审报告

> 评审人：首席架构师 · 评审基准：architecture-v2 文字权威 + ADR-0008 跨层 DAG + CONSTRAINTS 34 铁律
> 范围：12 层真实映射 + 4 条端到端业务流 + 对抗验证后确认的代码审查发现

---

## 一、平台运行逻辑梳理

### 1.1 平台真实是怎么跑起来的（对标 architecture-v2）

整套系统的"装配-表现-业务-数据"四段式跑法已经成型，跟业界 SOC 平台（Charlotte/Copilot/QAX-GPT）的"前端壳 + Agent 编排 + 网关治理 + 数据底座"分层是一个路子，关键的合规骨架立住了：

**组合根 + 表现层（L01）**：进程启动时 `runtime.py` 的 `Runtime` 单例一次性把 L02–L12 共 10 个层的 store/gateway/service 全部 wire 好（PG/内存仓储、LLM 网关、AgentContext、审计链、降噪引擎），以全局 `rt` 暴露；`api.py` 薄装配 16 个域 router、约 66 个 REST 端点。**FastAPI/HTTP 知识严格只在 L01**——已 grep 验证 L02–L12 内 `fastapi` import 为 0。这正是 ADR-0011 描述的合规模式：组合根天然要 wire 所有层，不算违反 DAG。

**业务出口（L07）+ Agent 编排（L02）**：所有业务调用（分诊/调查/关联/报表）经 L07 Service 包一层，构造 `Task` 交给 L02 `Orchestrator.dispatch` 按 `task.kind` 路由给对应 Agent（C-5 合规，不是 itops 那种 9 个扁平 Agent）。

**网关治理（L05）**：所有 LLM 调用必经 `LLMGateway.call`（C-6），网关内串起预算闸门→出域过滤→场景路由→脱敏→cross-check/降级链→schema 校验→计费→metadata 上报。这一层是全平台最成熟的部分，接近生产。

**横切支撑（L12/L06）**：L12 提供 secrets(Fernet/scrypt)、config、db 连接池、audit 哈希链、OTel；L06 提供 ToolRegistry + ES 薄适配器 + Notifier，是出站治理边界。

**数据面（L08/L09/L10/L11）**：L08 算法（降噪/关联/IoC）、L09 衍生数据仓储（告警/事件/报表）、L10 归一化、L11 资产 CMDB。这一面整体偏薄，多数是"够闭环用"的最小实现。

### 1.2 四条核心业务流真实调用链

| 业务流 | 真实链路 | 落库 | 合规要点 |
|---|---|---|---|
| **告警分诊** | L01 `/api/triage` → CMDB 富化 → L07 `AlertTriageService` → L02 `Orchestrator→TriageAgent` → L06 ES 富化 → L05 网关研判 → 真威胁自动建 HITL 工单 | 真落库（Memory/工单 PG），审计 2 处 | C-5/6/8/20/21/26/27 齐，最完整 |
| **事件调查** | L01 `/api/investigate` → L07 `InvestigationService` → `Orchestrator→InvestigationAgent` → ES 时间线 + LLM 攻击链 | **结论不落库**，仅审计（内存） | C-24 引用弱、cross-check 从不启用、硬编码阈值未读 agent_config |
| **降噪→关联→建事件** | `/api/ingest/alert`(L10归一→L08降噪→L09入库) + `/api/correlate`(L08并查集→L02 CorrelationAgent→L05) + `/api/events/confirm`(人工确认建事件) | 真落库（告警/事件/抑制规则全可 PG） | C-4 混合架构标准范例（确定性聚簇 + LLM 仅叙述），confirm 不校验 alert_ids 归属 |
| **SOAR→外发→HITL** | `/api/soar/trigger`(建待审工单+run) + `/api/tickets/{id}/approve`(批准→执行) + `/api/dispatch/run`(L06 notifier) + `/api/soar/runs/{id}/undo` | 仓储 PG，但**审计链仅内存** | C-8/32 合规；执行/撤销是占位（不真正经 L06 下发处置） |

### 1.3 与架构图一致 / 偏离处

**一致（架构骨架立住）**：
- 组合根装配全层、FastAPI 零渗透下游（ADR-0011 标准实现）
- Orchestrator 必经（C-5）、LLM 必经网关（C-6）、工具必经 ToolRegistry（C-22 边界存在）
- C-4 混合架构落地：降噪指纹/并查集/IoC 都是确定性算法，LLM 只在 L07 做叙述定性
- 闭环已通：采集→降噪→分诊→关联→事件→SOAR→外发→HITL→报表

**偏离（须留意）**：
- **L03 RAG 整层零代码**，Chat 挂件与 Investigation 上下文增强绕过整层直连 L05
- **Prompt 治理热加载断路**：L04 PromptStore 已实现，但 L02 三个 Agent 仍用硬编码 prompt，UI 改 prompt 不影响 Agent 行为
- **7+1 Agent 群只落地 3 个**（Reporter/Intel/Tuning 缺失），反馈飞轮 L01→L02(Tuning) 唯一合法向上边在代码层完全断裂
- **数据面越级**：`routers/alerts.py` 在表现层直接编排 L10→L08→L09 写入流水线（超出"薄 CRUD 读"豁免）
- **asset_cmdb 层归属错位**：按 v2 应在 L12，实际落在 L11

---

## 二、实现级别评估

### 2.1 成熟度矩阵

| 层 | 定级 | 一句话依据 |
|---|---|---|
| L01 人机交互 | **可用** | 组合根 + 16 router + ~66 端点 + 17 项 IA 实页接真；差零鉴权、L10 越级、路由层改写单例 |
| L02 Agent 群+平台核心 | **可用** | Orchestrator + 3 真 Agent + 工单/SOAR/通知/RBAC 全仓储可 PG；缺 4+1 Agent、Prompt 治理错位、无 token 鉴权 |
| L03 RAG Pipeline | **占位** | 唯一零代码层，`__init__.py` 0 字节，Reranker(C-7 必备★) 缺失 |
| L04 Models&Knowledge | **玩具** | 仅 prompt_store(~190 行)；致命：Agent 用硬编码 prompt，治理形同虚设 |
| L05 Gateway | **接近生产** | LLM Gateway 全覆盖且单测齐；缺 api_gateway 整子目录、无熔断器、metadata 仅内存 |
| L06 MCP Server 群 | **玩具** | 6 类只落 2 个；出站白名单仅 IP 段硬编码，凭证直读 .env 未走 secrets |
| L07 AISecOps 能力 | **可用** | 4 真出口满足 C-1「至少 4」；缺 threat_hunting/ueba/vuln_compliance |
| L08 Analytics | **玩具** | 3/12 子模块；安全侧 attack_graph/kill_chain/ueba(C-2)/compromise 全缺 |
| L09 Data Platform | **玩具** | 实为衍生数据仓储层；数据中台 6 子组件 0 实现（已声明延后） |
| L10 Data Collection | **占位** | 仅 normalize_alert 一个 53 行纯函数，覆盖率约 5%（已声明延后） |
| L11 Target Estate | **玩具** | 仅迷你 CMDB；5 子组件全缺，ai_compliance(C-3) 缺失，asset_cmdb 层归属错位 |
| L12 Core Support | **可用** | 全平台横切核心（secrets/config/db/audit/OTel）被 11 处依赖；audit 仅内存、scheduling 缺失 |

### 2.2 架构覆盖度

**已实现**：Orchestrator(C-5)、Triage/Investigation Agent、LLM Gateway 横切(C-6/18/30/33/34/32)、HITL Channel(C-8)。

**部分**：Enrichment Agent（内嵌无法独立路由）、L08 安全分析算法（仅 ioc 字符串匹配）、L08 AIOps 算法（仅 correlation+dedup）、L12 四件套（secrets/observability 有，asset_cmdb 错位、scheduling 缺）、6 大 SEC 出口（4 真）、ADR-0009 ES 就地查询（多源接入延后）。

**缺失**：Responder/Reporter/Intel/Tuning Agent、反馈飞轮(L01→L02 Tuning)、Reranker(C-7★)、RAG 其余 4 件、API Gateway(入向限流/鉴权/审计)、L11 ai_compliance(C-3)、L08 attack_graph/kill_chain/ueba/compromise。

**已声明延后（合规）**：DSLM 群(P3+)、L09 数据中台、L10 多源日志接入。

### 2.3 34 铁律合规快照（仅列非"满足"项）

| 铁律 | 状态 | 说明 |
|---|---|---|
| C-3 ai_compliance 必须实质 | **违反** | L11 仅 README 零代码，Shadow AI/AI 模型审计未落地 |
| C-7 Reranker 必备 | **违反** | L03 整层零代码 |
| 会话令牌鉴权 | **违反** | 无 token 签发、端点无鉴权守卫（CLAUDE.md 已知 TODO） |
| README 状态同步 | **违反** | L04/05/06/07/08/09/11/12 多个 README 仍写「占位」，与代码严重不符 |
| C-2 L08 安全侧算法 | 部分 | 仅 ioc 字符串匹配，attack_graph/kill_chain/ueba/compromise 全缺 |
| C-9 凭证位于 L12 secrets | 部分 | L06 ES 凭证直读 .env 未经 secrets 加密 |
| C-20 Prompt Injection 沙箱 | 部分 | 标签软隔离 + f-string 直插，未转义闭合标签 |
| C-22 出站白名单 | 部分 | 仅 IP 段硬编码 + 总开关，无细粒度许可列表 |
| C-23 不可篡改审计链 | 部分 | 哈希链成立但仅内存，重启即丢 |
| C-24 引用 | 部分 | 关联流强制 refs/citations，investigation 攻击链无强制引用 |
| C-27 高风险 cross-check | 部分 | 字符串全等比对、provider<2 静默退化、investigation 从不启用 |
| C-33 metadata 落库 | 部分 | OTel 聚合达成，明细仅内存、缺 agent_name/trace_id、cross-check 漏记 B 成本 |
| P-18 写动作持久化 | 部分 | 业务数据可 PG，审计链不落库 |

### 2.4 整体定级

> **核心安全运营闭环（采集→降噪→分诊→关联→事件→SOAR→外发→HITL→报表）已达「可用 Demo+」级，L05 网关接近生产。** 但 L03 RAG/Reranker(C-7)、L08 安全分析算法、L11 ai_compliance(C-3)、会话鉴权与审计落库缺失，数据中台 L09/L10 与 7+1 Agent 群尚未生产级。
>
> **结论：可用 Demo，离生产有结构性缺口。**

---

## 三、代码审查发现

> 全部经对抗验证（confirmed=2 票确认；contested=1 票存疑）。严重度为两位评审 adjusted_severity 收敛后取值。无 P0 残留——三条原 P0 均因 ADR-0003 自用定位 + CLAUDE.md 已声明 TODO 被一致下调为 P1，但**它们仍是上线前的硬阻断项**。

### 3.1 P1（上线前必须收口）

| # | 问题 | 文件:行 | 铁律 | 修复建议 |
|---|---|---|---|---|
| 1 | **所有写/审批端点无服务端鉴权**——匿名可批准工单/执行 SOAR/改配置/增删用户 | api.py:37-58；tickets.py:60 | C-8 | 登录签发会话令牌，写端点统一 `Depends(require_role)`，未带令牌返回 401 |
| 2 | **HITL 出站无目的地白名单 + 内网 SSRF**——连通测试/外发可指向 127.x/RFC1918，出域关时反而放行内网 | notifier.py:52；adapter_store.py:183-193 | C-22 | 落地 host/CIDR allowlist，解析后 IP 落 RFC1918/127/169.254/::1/fc00::/7 一律拒绝，禁 0.0.0.0/0 |
| 3 | **硬编码默认管理员口令 `aisecops`**——首启写入生产 PG，admin 不可删 | users.py:162-167 | C-9 | 生产不种弱口令，首启随机生成/环境变量注入 + 强制改密，仅 dev/CI 标志下 seed |
| 4 | **审计哈希链仅内存、重启即丢**——HITL 审批/SOAR 执行/配置变更留痕不耐久 | base.py:47；L12/audit.py | C-23 | 新增 PgAuditStore(append-only 表)，runtime 注入；DB 侧禁 UPDATE/DELETE |
| 5 | **审计 actor 由客户端自报、默认「未知」**——审计主体可任意伪造，问责链失效 | routers/tickets.py:20-42 | C-23 | actor 必须由服务端从会话令牌解析的已认证身份赋值，忽略请求体 actor（随 #1 一并闭合） |
| 6 | **cross-check 用全文逐字符比对**——结构化研判几乎必然判不一致，退化成「高风险一律 abstain」 | gateway.py:163 | C-27 | schema 解析后比关键决策字段（verdict / is_incident+severity），自由文本不参与 |
| 7 | **cross-check 双模型只记 A 的 token**——成本/预算系统性低估约 50%，月度闸门被绕过 | gateway.py:158 | C-33/C-27 | 两次用量按各自单价折算相加，budget.record 记合计，metadata 体现明细 |
| 8 | **分诊/调查/关联调用从不传 seed**——temp=0 仍不可复现，HITL 无法复盘 | triage.py:74；investigation.py:70；correlation.py:87 | C-30 | 研判场景注入确定性默认 seed，CallMetadata 记录实际 seed |
| 9 | **降级链只 catch ProviderError**——畸形 JSON 响应体抛 `json.JSONDecodeError` 绕过末位 stub 直接 500 | fallback.py:45 | C-34 | 循环内放宽为 `except Exception`，CancelledError 单独 re-raise；或 provider 内统一转 ProviderError |
| 10 | **CallMetadata 缺 agent_name/trace_id**——调用无法回溯到发起 Agent / 端到端请求 | models.py:48 | C-33 | call() 增 agent_name/trace_id 形参，写入 metadata 并随 OTel 上报 |
| 11 | **Correlation 攻击链 refs/citations 不校验真伪**——LLM 可臆造 ALERT-9999，平台照单全收 | correlation.py:93 | C-24 | 解析后用本簇合法 id 集合校验 refs，越界剔除，全空/全非法则强制 abstain |
| 12 | **加密主密钥未配时静默回退固定 dev 密钥**——漏配则敏感配置形同明文 | secrets.py:23-33 | C-9 | 生产 fail-closed：非 dev/CI 且未配 AISECOPS_MASTER_KEY 直接拒绝启动 |
| 13 | **出域脱敏规则过窄**——文件哈希/域名/主机名/IoC 未脱敏即送海外 LLM | desensitize.py:13-25 | C-32 | 扩规则覆盖 MD5/SHA1/SHA256/域名/URL/主机名/SID，加脱敏覆盖率单测 |
| 14 | **降噪时间窗：ts 不可解析时错误归并**——同指纹新告警被静默折叠（防御性缺陷） | dedup.py:249 | — | 改为 `if ats is not None and ... <= window` 命中才 merge，宁可少合并不可吞告警 |
| 15 | **PG 工单审批 SELECT-then-UPDATE 无行锁**——并发批准可双执行 SOAR 处置 | tickets.py:166 | C-8 | 条件 UPDATE 原子 CAS：`UPDATE ... WHERE seq=%s AND status='待审' RETURNING ...` |

> 注：#14/#15 两位评审有部分下调到 P2/P3 的意见（依赖触发路径在当前代码是否可达），此处取较高者保留可见性。

### 3.2 P2（应修，影响可用性/合规质量）

| # | 问题 | 文件:行 | 铁律 | 修复建议 |
|---|---|---|---|---|
| 16 | Investigation 攻击链推断从不做 cross-check，无 high_risk 入口 | investigation.py:70 | C-27 | 接 `config_for('investigation')` + `resolve_cross_check`，service/router 透传 high_risk |
| 17 | Triage/Investigation ES 日志裸 str() 拼进沙箱标签，未转义闭合标签 | triage.py:60；investigation.py:64 | C-20 | 拼接前中性化 `</related_logs>`/`</logs>`，或用一次性 nonce 边界 + 截断长度 |
| 18 | 全 provider 失败/预算超限/schema 失败无业务层 HITL 兜底，直接 500 | orchestrator.py:29 | C-34/C-26 | dispatch/run 外层捕获三异常，转 abstain=待研判 AgentResult + 建 HITL 工单 |
| 19 | 非 stub provider schema 校验失败直接抛，无重试/降级 | gateway.py:191 | C-34/C-21 | 校验失败降级到下一 provider 带强格式指令重试，仍失败回退 stub/abstain |
| 20 | 出域脱敏仅依据 provider.outbound 标志，端点误判则原文出域 | gateway.py:106-114；outbound_switch.py | C-32 | 脱敏与"provider 是否第三方/海外"解耦，非本地自托管默认脱敏 |
| 21 | ingest 严重度非映射表值原样透传，污染四级枚举 | ingest.py:34 | — | 未命中回退安全默认级 + 记 observability；或 Alert.severity 加 Literal 约束 |
| 22 | 分诊真威胁自动建单未写审计，HITL 链起点不可追溯 | alert_triage.py:37-40 | C-23 | 建单后 audit.append(action='ticket_auto_create')，source_alert 用真实告警 id |
| 23 | L01 ingest 路由在表现层编排数据面流水线(L10→L08→L09)，超 ADR-0011 豁免 | routers/alerts.py:23-48 | ADR-0008/0011 | 下沉为 L07 ingest 出口或 L09 ingest pipeline，路由只调出口 |

> 注：#23 两位评审均倾向 P3（结构债，非功能 bug），此处保留在 P2 边界以提示其架构意义。

### 3.3 P3（技术债/加固项）

| # | 问题 | 文件:行 | 修复方向 |
|---|---|---|---|
| 24 | L01 表现层内联降噪统计计算，与 reporting.py 口径分裂 | routers/alerts.py:69-98 | 收敛到 L09 `dedupe_stats()`，两处共用 |
| 25 | `172.` 私网判定缺位数校验，`10.example.com` 类域名误判为内网 | outbound_switch.py:22 | 用 `ipaddress` 模块判 IP，非 IP 一律视为出域 |
| 26 | SOAR undo 撤销已执行处置不经 HITL（当前占位故 P3，接真前必收口） | routers/soar.py:112-124 | undo 也纳入 HITL 审批，执行/撤销落地真实 L06 调用 |

### 3.4 Contested（存疑，1 票确认 1 票证伪）

| # | 问题 | 文件:行 | 分歧点 |
|---|---|---|---|
| C1 | Chat 助手 stub 离线返回空内容当真实回答（C-26/24 弱化） | triage_chat.py:69 | 一票认为前端有 stub 徽章 + stub 内容是带标签的输入回显，不构成幻觉，仅 UX 打磨点；一票认为 chat 路径缺诚实兜底话术成立但轻微。**结论：偏 UX，非安全违规** |
| C2 | alert_stats pending 口径含「新」+ by_source 跳过空 source | alert_store.py:250 | 一票认为事实成立但属语义/口径问题非 bug；一票认为"占比环图对不上"反事实（实际无饼图消费者）。**结论：琐碎 nitpick** |

---

## 四、行动建议（按优先级）

### 第一梯队：上线前硬阻断（鉴权 + 审计三件套）

这四件互相耦合，建议作为一个 Sprint 一起做：

1. **补会话令牌鉴权（#1）** —— 登录签发 token，写端点统一 `Depends(require_role)`。这是所有安全控制的地基，不做则 C-8 人审、RBAC、审计问责全部形同虚设。
2. **审计 actor 由服务端身份赋值（#5）** —— 随 #1 顺带闭合，否则审计链「谁做的」可任意伪造。
3. **审计链落 PG（#4）** —— 按现有仓储模式新增 PgAuditStore，否则「不可篡改审计贯穿」在重启后归零，名实不符。
4. **去掉硬编码默认口令 + 主密钥 fail-closed（#3/#12）** —— 生产不种 `aisecops` 弱口令、不静默用公开 dev 密钥，二者都是"漏配即裸奔"。

### 第二梯队：网关治理修真（成本与可复现是自用刚需）

L05 是最成熟的层，但有几个治理细节让"自用关键"的成本/复现能力打折：

5. **cross-check 改字段级比对（#6）** —— 当前逐字符比对让高风险研判退化成"一律转人工"，cross-check 形同虚设。
6. **cross-check 双模型成本全记 + seed 注入（#7/#8）** —— 预算闸门系统性低估 50%、研判不可复现，都直接影响自用账本与 HITL 复盘。
7. **降级链兜底放宽 + schema 失败降级（#9/#19/#18）** —— 三个一起做，让"LLM 全挂/吐坏 JSON/预算耗尽"都优雅降级到 abstain/HITL，而非 500。

### 第三梯队：SSRF 与脱敏（出站面收口）

8. **L06 落地目的地白名单（#2）** —— 把 registry.py 注释承诺的"白名单"落成代码，堵内网 SSRF。
9. **扩脱敏规则 + 解耦脱敏触发（#13/#20）** —— 哈希/域名/主机名进脱敏集，避免客户 IoC 裸送海外 LLM。

### 第四梯队：架构补齐（按业务触发节奏）

10. **打通 Prompt 热加载** —— L02 三个 Agent 从 L04 PromptStore 读 active 版本，否则 UI 改 prompt 是假按钮。
11. **Investigation 接 cross-check + 引用校验（#16/#11/#17）** —— 让调查流与分诊/关联拉平，攻击链 refs 校验真伪。
12. **数据面越级整改（#23/#24）** —— ingest 流水线下沉 L07/L09，降噪统计口径收敛。
13. **按需补 L03 Reranker（C-7）、L08 安全算法（C-2）、L11 ai_compliance（C-3）** —— 这三条是硬铁律违反，但属"业务尚未触发"的延后；一旦上 RAG 检索/攻击图/AI 资产审计就必须先补，否则违反铁律。

### 收尾：文档同步

14. **更新 8 个层的 README 状态** —— L04/05/06/07/08/09/11/12 仍写「占位」，与已落地代码严重不符，属工程纪律违规，且会误导后续开发者判断完成度。

---

**一句话总结**：骨架合规、闭环跑通、网关接近生产，是一个**值得继续投入的扎实 Demo+**；但鉴权与审计落库这组硬阻断不解决就不能称"可用于真实 SOC"，而成本计量/cross-check/seed 这几个网关细节是自用场景最该先擦亮的——它们不影响 Demo 演示，却直接决定平台"上真实 LLM 后是否可信"。
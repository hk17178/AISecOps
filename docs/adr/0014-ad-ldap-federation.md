# ADR-0014 · 域控 AD/LDAP 登录联邦 + 工单派发到 AD 账号

- 状态：已接受
- 日期：2026-06-05
- 相关：[架构补齐计划 Phase 5](../specs/architecture-gap-plan.md) · ADR-0003 自用定位 · L02 IAM · L06 protocols

## 背景

用户反馈⑥：希望能用域控（AD/LDAP）账号登录，并把工单自动派发到域控账号。现有 IAM 是本地用户表
（scrypt 口令）。单组织 AD 集成是自用合理诉求，**不违反 ADR-0003**（不做多租户/商业化）。

## 决策

### 1. 认证联邦（Authenticator 抽象，L02 IAM）
把登录认证抽象成 `Authenticator.authenticate(username, password) -> Principal | None`，两实现：
- `LocalAuthenticator`：现有本地用户表（默认）。
- `LdapAuthenticator`：bind 到 AD/LDAP，按 **AD 组 → 平台三角色** 映射（如 `SecAdmins→管理员`）。

**选择规则**：配置了 `LDAP_URL` 用 LDAP，否则本地。二者可共存（LDAP 失败可留本地兜底账号）。

### 2. stub-first + 依赖注入（守 C-17/C-18 精神）
LDAP 离线/CI 连不上真服务器：
- `LdapAuthenticator` 的 **bind / 取组** 可注入（测试传假实现，验证"组→角色映射"逻辑，不连真 LDAP）。
- 真实现 **lazy import `ldap3`**（只有真配置 LDAP 才需要装），未装而又配了 LDAP → 明确报错，不静默。
- 未配 LDAP → 根本不碰 ldap3，本地账号照常。**不做假"已接 AD"按钮。**

### 3. 工单派发到 AD 账号（接 Phase 2 协作态）
工单 `assignee` 字段（ADR-0012 已加）即可填 AD 账号。新增"自动派发"：
- 配 `DEFAULT_ASSIGNEE` 后，自动建的 HITL 工单（Responder）默认指派给该处理人（可为 AD 账号）+ 留痕。
- 后续可扩"按规则/轮询派发" + 经通知中枢通知到人。

### 4. 配置（走 .env / 系统设置）
`LDAP_URL` / `LDAP_BASE_DN` / `LDAP_USER_TEMPLATE`（如 `uid={username},ou=people,dc=corp`）/
`LDAP_ROLE_MAP`（JSON：AD 组→角色）/ `DEFAULT_ASSIGNEE`。

## 后果
- 正面：支持企业 AD 单点登录；工单可派到真人/AD 账号；本地账号仍可兜底。
- 负面：多一个可选依赖 ldap3（lazy，未用不装）；AD 映射需运维配置。
- 风险：LDAP 不可达时不能把所有人锁在门外 → 保留本地兜底账号（admin）。

## 关联
- ADR-0003（自用，不做多租户）· ADR-0012（工单协作态）· CONSTRAINTS C-9（凭证）· C-17/C-18（stub）

# ADR-0010 · P0 环境决策落定 + Docker 运行时用 Colima

- 状态：Accepted
- 日期：2026-06-04
- 决策者：muzi
- 关联：落定 [PRD §9 待决策](../specs/PRD.md)；Docker 选型（P-12 零运维）

## 背景

PRD §9 还剩 4 条待决策（部署 / SIEM-EDR / 通知 / CMDB）需要真实环境信息；同时本机需要装 Docker 才能跑 `make dev`。本 ADR 一次性落定。

## 决策

### P0 环境决策（PRD §9）

| 项 | 决定 | 影响 |
|---|---|---|
| **部署在哪** | **本机 Mac 先跑（PoC）** | 单机 docker-compose；以后同事用了再上公司服务器 |
| **SIEM/EDR** | **暂只接 ES**（见 [ADR-0009](0009-logs-in-elasticsearch-query-in-place.md)） | L06 的 P0 连接器只做 **ES 适配器**；别的 SIEM/EDR 待真需求再加 |
| **通知中枢** | **企业微信（首个）** | L02 通知用企微机器人 webhook；`.env` 配 `WECHAT_WEBHOOK`；钉钉/邮件以后扩展 |
| **资产 CMDB** | **暂不接** | L11 资产先留空 / 手填；告警富化暂不依赖 CMDB，等有资产源再补 |
| LLM | API key 接入（已定，[L05](../specs/L05-impl-plan.md)） | OpenAI 兼容 provider，配 `.env` / 将来 UI（P-18） |

### Docker 运行时：Colima（不用 Docker Desktop）

选 **Colima**（+ brew 的 docker / docker-compose）而非 Docker Desktop：

- 轻量、**无 GUI、无许可证**、命令行就能起，贴 [P-12 零运维]。
- macOS arm64 上验证通过：PG(pgvector) + Redis 容器均 healthy。

**Colima 使用备忘（写给未来的自己）**：

```bash
brew install colima docker docker-compose
colima start                 # 起 Docker daemon（首次下载 VM 镜像）
# 让 `docker compose`(插件式) 可用：
ln -sfn "$(brew --prefix docker-compose)/bin/docker-compose" ~/.docker/cli-plugins/docker-compose
# 去掉旧 Docker Desktop 残留的凭证助手(否则拉镜像报 docker-credential-desktop not found)：
#   编辑 ~/.docker/config.json 删除 "credsStore": "desktop"
make dev                     # 起 PG + Redis
colima stop                  # 不用时停
```

## 后果

**正面**：环境决策不再悬空，L06/L11 范围收窄（只 ES、不做 CMDB）→ Sprint 4 更聚焦；Docker 轻量零许可。
**负面 / 风险**：
- 本机 PoC：电脑睡眠/重启后容器需重起（`colima start && make dev`）；不适合长期给同事用 → 同事真用时迁公司服务器（数据用卷持久化，迁移成本可控）。
- 只接 ES + 无 CMDB：富化维度暂少（无资产重要度）→ 有数据源后增量补，不影响主链路。

## 关联

- [PRD §9](../specs/PRD.md) · [ADR-0009 ES 日志](0009-logs-in-elasticsearch-query-in-place.md) · [PRINCIPLES P-12/P-18](../../PRINCIPLES.md)
- [restart-guide](../restart-guide.md)（Colima 启动步骤）

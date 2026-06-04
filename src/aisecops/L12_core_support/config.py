"""L12 · 配置（读 .env，凭证零硬编码 —— O4 / CONSTRAINTS C-9）。

所有密码 / API Key 走环境变量或 .env，不写进代码。
跨层定位（ADR-0008）：L12 横切支撑，任何层可读配置。

⚠️ 临时形态：`.env` 仅作"首次引导/开发用"。按 [PRINCIPLES P-18] 配置应走 Web
（系统设置页）管理 + 存 DB + 密钥加密，随 L01/L02 落地后这里改为"DB 优先、.env 兜底"。
读取入口 get_settings() 保持稳定，届时换数据源不影响调用方。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """平台运行配置。字段名对应 .env 里的大写变量（大小写不敏感）。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- LLM（L05 Gateway）----
    # 留空则只用 stub（不联网）；填了 key 即用真 provider。
    llm_api_key: str = ""
    llm_base_url: str = "http://localhost:11434/v1"  # 默认本地 Ollama；SaaS 改成对应地址
    llm_model: str = "qwen2.5"
    llm_price_per_1k_cny: float = 0.0  # 每 1k token 价格，用于成本核算

    # ---- 预算 / 出域 ----
    monthly_budget_cny: float = 500.0
    allow_outbound: bool = False  # 出域开关（C-32，默认关）

    # ---- 数据源 Elasticsearch（日志主存，ADR-0009）----
    # 留空 es_api_key 且无用户名密码 → 用 StubLogSource（离线假日志）
    es_hosts: str = "http://localhost:9200"
    es_api_key: str = ""
    es_username: str = ""
    es_password: str = ""
    es_index: str = "*"

    # ---- 通知（首个=企业微信，ADR-0010）----
    wechat_webhook: str = ""

    # ---- 持久化（P-18）----
    # 留空 → 内存存储（重启丢，CI/快速开发用）；填 postgresql://... → PG 持久化
    database_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """取全局配置（带缓存）。"""
    return Settings()

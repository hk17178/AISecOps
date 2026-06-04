"""L12 · 系统配置持久化（P-18：配置走 DB，密钥加密）。

替换"内存暂存"：配置经 UI 改 → 存 DB；敏感键（API Key/webhook）入库前加密
（见 secrets.SECRET_KEYS）。读时解密供平台使用；对外 API 只回"是否已配置"，不回明文。
仓储模式：默认内存，配 DATABASE_URL 用 PG。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .secrets import SECRET_KEYS, decrypt_secret, encrypt_secret


class ConfigStore(ABC):
    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """存一项配置（敏感键自动加密）。"""
        raise NotImplementedError

    @abstractmethod
    def all_decrypted(self) -> dict[str, str]:
        """全部配置（敏感键已解密，供平台内部用）。"""
        raise NotImplementedError


class InMemoryConfigStore(ConfigStore):
    def __init__(self) -> None:
        self._items: dict[str, tuple[str, bool]] = {}  # key -> (stored_value, is_secret)

    def set(self, key: str, value: str) -> None:
        is_secret = key in SECRET_KEYS
        self._items[key] = (encrypt_secret(value) if is_secret else value, is_secret)

    def all_decrypted(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for k, (v, is_secret) in self._items.items():
            out[k] = decrypt_secret(v) if is_secret else v
        return out


class PgConfigStore(ConfigStore):
    def __init__(self, database_url: str) -> None:
        from .db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS app_config ("
                "key text PRIMARY KEY, value text, is_secret boolean DEFAULT false)"
            )

    def set(self, key: str, value: str) -> None:
        is_secret = key in SECRET_KEYS
        stored = encrypt_secret(value) if is_secret else value
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO app_config (key, value, is_secret) VALUES (%s,%s,%s) "
                "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, is_secret=EXCLUDED.is_secret",
                (key, stored, is_secret),
            )

    def all_decrypted(self) -> dict[str, str]:
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT key, value, is_secret FROM app_config").fetchall()
        out: dict[str, str] = {}
        for r in rows:
            out[r[0]] = decrypt_secret(r[1]) if r[2] else (r[1] or "")
        return out


def build_config_store(database_url: str = "") -> ConfigStore:
    if database_url:
        try:
            return PgConfigStore(database_url)
        except Exception:
            pass
    return InMemoryConfigStore()


# 可在 UI 改并持久化的键（含敏感与非敏感）
EDITABLE_KEYS = (
    "llm_api_key",
    "llm_base_url",
    "llm_model",
    "monthly_budget_cny",
    "allow_outbound",
    "es_hosts",
    "wechat_webhook",
)


def coerce(key: str, raw: Any) -> str:
    """把入参规整为字符串存储（bool/数字转字符串）。"""
    if isinstance(raw, bool):
        return "true" if raw else "false"
    return str(raw)

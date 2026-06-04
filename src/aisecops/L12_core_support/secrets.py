"""L12 · 密钥与口令（C-9 / P-18）。

两件事：
1. **配置密钥加密**：API Key / webhook 等敏感配置入库前用 Fernet 对称加密，不落明文。
   主密钥来自环境变量 AISECOPS_MASTER_KEY（Fernet key）；没配则用派生的 dev key（仅
   开发/CI，生产必须配）。
2. **用户口令哈希**：用 stdlib scrypt 加盐哈希，不可逆，不存明文。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken

# 入库需加密的敏感配置键
SECRET_KEYS = {"llm_api_key", "wechat_webhook", "es_api_key", "es_password"}


def _derive_dev_key() -> bytes:
    """开发兜底主密钥（固定派生；仅 dev/CI，生产必须配 AISECOPS_MASTER_KEY）。"""
    digest = hashlib.sha256(b"aisecops-dev-master-key-not-for-prod").digest()
    return base64.urlsafe_b64encode(digest)


def _fernet(master_key: str = "") -> Fernet:
    key = master_key or os.environ.get("AISECOPS_MASTER_KEY", "")
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    return Fernet(_derive_dev_key())


def encrypt_secret(plain: str, master_key: str = "") -> str:
    if plain == "":
        return ""
    return _fernet(master_key).encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str, master_key: str = "") -> str:
    if not token:
        return ""
    try:
        return _fernet(master_key).decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""  # 主密钥变更/数据损坏 → 当作未配置，不崩


def hash_password(password: str) -> str:
    """scrypt 加盐哈希，返回 'salt$hash'（hex）。"""
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False

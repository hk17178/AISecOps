"""L03 · 文本向量化（Embedding）。

默认 `HashingEmbedder`：本地确定性 hashing 向量（词 + 字符 3-gram 散列到固定维度 + L2 归一化），
**离线、可复现、零依赖**，适合自用与 CI。接口稳定，生产可无缝换成经 L05 网关的真 embedding
模型（豆包/通义，受出域开关 + 脱敏约束 C-32），调用方不变。
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

_TOKEN = re.compile(r"[\w一-鿿]+")


def tokenize(text: str) -> list[str]:
    """粗分词：英文按词、中文按字（够检索召回用，零依赖）。"""
    out: list[str] = []
    for m in _TOKEN.findall(text.lower()):
        if m.isascii():
            out.append(m)
        else:
            out.extend(list(m))  # 中文逐字
    return out


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class Embedder(Protocol):
    """向量化器契约。"""

    dim: int

    def embed(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """确定性 hashing 向量化（feature hashing / hashing trick）。

    把词与字符 3-gram 用带符号散列累加到固定维度，再 L2 归一化。无需模型/网络，
    同输入同输出（C-30 友好），余弦相似度即两向量点积。
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        lowered = text.lower()
        features = tokenize(text)
        # 加字符 3-gram，提升对短文本/局部相似的召回
        features += [lowered[i : i + 3] for i in range(max(0, len(lowered) - 2))]
        for feat in features:
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        return _l2_normalize(vec)

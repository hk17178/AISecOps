"""L03 · 分块（Chunking）。

把长文档切成检索粒度的块：优先按段落聚合到目标长度，超长段落硬切并带重叠
（overlap 保证跨块语境不丢）。结构感知的最小可用版，够案例/手册类语料用。
"""

from __future__ import annotations


def chunk_text(text: str, size: int = 400, overlap: int = 80) -> list[str]:
    """把文本切成约 size 字符的块（按段聚合，超长段落带 overlap 硬切）。"""
    text = text.strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 1 <= size:
            buf = f"{buf}\n{para}".strip()
            continue
        if buf:
            chunks.append(buf)
            buf = ""
        if len(para) <= size:
            buf = para
        else:
            step = max(1, size - overlap)
            for i in range(0, len(para), step):
                chunks.append(para[i : i + size])
    if buf:
        chunks.append(buf)
    return chunks

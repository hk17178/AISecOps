"""OpenAICompatProvider —— 通用 OpenAI 兼容接口 provider（API Key 接入）。

适配几乎所有主流 LLM：OpenAI / 豆包 / 通义 / 智谱 / DeepSeek / 本地 vLLM·Ollama
——它们大多提供 `/v1/chat/completions` 兼容端点。只需配 base_url + api_key + model。
"""

from __future__ import annotations

import httpx

from ..models import LLMRequest, TokenUsage
from ..outbound_switch import is_outbound_url
from .base import Provider, ProviderError


class OpenAICompatProvider(Provider):
    """调用 OpenAI 兼容的 /chat/completions 端点。"""

    name = "openai_compat"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        price_per_1k_cny: float = 0.0,
        timeout: float = 30.0,
        name: str | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.price_per_1k_cny = price_per_1k_cny
        self.timeout = timeout
        # 自动判定是否出域：本地端点不算，公网端点算（C-32）
        self.outbound = is_outbound_url(base_url)

    async def complete(self, request: LLMRequest) -> tuple[str, TokenUsage]:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": m.role.value, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.name}[{self.model}] 调用失败：{exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
            usage_raw = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=int(usage_raw.get("prompt_tokens", 0)),
                completion_tokens=int(usage_raw.get("completion_tokens", 0)),
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.name} 响应格式异常：{exc}") from exc
        return content, usage

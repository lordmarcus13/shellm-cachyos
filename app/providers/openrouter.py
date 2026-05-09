from __future__ import annotations
import httpx
from typing import Iterable, Dict, Any

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS = "https://openrouter.ai/api/v1/models"

class OpenRouterProvider:
    name = "openrouter"
    def __init__(self, api_key: str): self.api_key = api_key
    async def list_models(self) -> list[dict]:
        headers = {"Content-Type": "application/json", "HTTP-Referer": "http://localhost", "X-Title": "shellm-win-pro-ext-r2"}
        if self.api_key: headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(OPENROUTER_MODELS, headers=headers)
            r.raise_for_status()
            return r.json().get("data", [])
    async def complete(self, messages: Iterable[Dict[str,str]], model: str | None = None, **gen_params: Any) -> str:
        if not self.api_key: raise RuntimeError("OpenRouter API key not provided")
        headers = {"Authorization": f"Bearer {self.api_key}", "HTTP-Referer": "http://localhost", "X-Title": "shellm-win-pro-ext-r2", "Content-Type": "application/json"}
        payload: dict[str, Any] = {"model": model or "qwen/qwen-2.5-72b-instruct", "messages": list(messages), "stream": False}
        for k in ("temperature","top_p","top_k","max_tokens"):
            if (v := gen_params.get(k)) is not None: payload[k] = v
        async with httpx.AsyncClient(timeout=920) as client:
            r = await client.post(OPENROUTER_ENDPOINT, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            content = data.get("choices",[{}])[0].get("message",{}).get("content")
            if not content: raise RuntimeError(f"Empty completion: {data}")
            return content

from __future__ import annotations
import httpx
from typing import Iterable, Dict, Any

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_TAGS = f"{OLLAMA_BASE_URL}/api/tags"
OLLAMA_CHAT = f"{OLLAMA_BASE_URL}/api/chat"

class LocalProvider:
    name = "local"
    
    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                r = await client.get(OLLAMA_TAGS)
                r.raise_for_status()
                data = r.json()
                return data.get("models", [])
            except Exception:
                return []
                
    async def complete(self, messages: Iterable[Dict[str,str]], model: str | None = None, **gen_params: Any) -> str:
        if not model:
            # Dynamically select first available model if none provided
            available = await self.list_models()
            if available:
                model = available[0].get("name", "llama3")
            else:
                model = "llama3"
                
        payload: dict[str, Any] = {
            "model": model, 
            "messages": list(messages), 
            "stream": False
        }
        
        # Inject standard generation params into Ollama options block
        options = {}
        if (temp := gen_params.get("temperature")) is not None: options["temperature"] = temp
        if (top_p := gen_params.get("top_p")) is not None: options["top_p"] = top_p
        if (top_k := gen_params.get("top_k")) is not None: options["top_k"] = top_k
        if (num_predict := gen_params.get("max_tokens")) is not None: options["num_predict"] = num_predict
        if (num_ctx := gen_params.get("num_ctx")) is not None: options["num_ctx"] = num_ctx
        if (repeat_penalty := gen_params.get("repeat_penalty")) is not None: options["repeat_penalty"] = repeat_penalty
        if (seed := gen_params.get("seed")) is not None: options["seed"] = seed
        
        if options:
            payload["options"] = options
            
        async with httpx.AsyncClient(timeout=900) as client:
            r = await client.post(OLLAMA_CHAT, json=payload)
            if r.status_code != 200:
                err_text = r.text
                try: err_text = r.json().get("error", r.text)
                except Exception: pass
                raise RuntimeError(f"Ollama API Error ({r.status_code}): {err_text}")
                
            data = r.json()
            content = data.get("message", {}).get("content")
            if not content: raise RuntimeError(f"Empty completion from local backend: {data}")
            return content

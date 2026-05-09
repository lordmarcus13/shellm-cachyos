from __future__ import annotations
import httpx
from typing import Iterable, Dict, Any

GEMINI_ENDPOINT_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_LIST = "https://generativelanguage.googleapis.com/v1beta/models"

class GeminiProvider:
    name = "gemini"
    def __init__(self, api_key: str | None): 
        self.api_key = api_key

    async def list_models(self) -> list[dict]:
        params = {"key": self.api_key} if self.api_key else {}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(GEMINI_LIST, params=params)
            r.raise_for_status()
            return r.json().get("models", [])

    async def complete(self, messages: Iterable[Dict[str,str]], model: str | None = None, **gen_params: Any) -> str:
        if not self.api_key: raise RuntimeError("Gemini API key not provided")
        use_model = (model or "gemini-1.5-flash-latest")
        
        # CODE QUALITY FIX: Simplified message construction logic
        contents = []
        system_parts = []
        
        for m in messages:
            role = m.get("role", "user").lower()
            text = m.get("content", "")
            
            if role == "system":
                # Collect system prompts separately as per API requirement
                if text: system_parts.append({"text": text})
            elif role == "model" or role == "assistant":
                 contents.append({"role": "model", "parts": [{"text": text}]})
            else:
                 # Map 'user' and others to 'user'
                 contents.append({"role": "user", "parts": [{"text": text}]})

        body: Dict[str, Any] = {"contents": contents}
        
        if system_parts:
            body["system_instruction"] = {"parts": system_parts}

        # Map generation config
        gc: Dict[str, Any] = {}
        if (t := gen_params.get("temperature")) is not None: gc["temperature"] = float(t)
        if (p := gen_params.get("top_p")) is not None: gc["topP"] = float(p)
        if (k := gen_params.get("top_k")) is not None: gc["topK"] = int(k)
        if (m := gen_params.get("max_tokens")) is not None: gc["maxOutputTokens"] = int(m)
        if gc: body["generationConfig"] = gc
        
        if (s := gen_params.get("safety")): body["safetySettings"] = s

        headers = {"Content-Type":"application/json"}
        params = {"key": self.api_key}
        
        async with httpx.AsyncClient(timeout=920) as client:
            r = await client.post(GEMINI_ENDPOINT_TMPL.format(model=use_model), headers=headers, params=params, json=body)
            if r.status_code >= 400:
                try: 
                    err_data = r.json()
                    msg = err_data.get("error", {}).get("message") or str(err_data)
                except Exception: 
                    msg = r.text
                raise RuntimeError(f"Gemini HTTP {r.status_code}: {msg}")
            data = r.json()
            
        cands = data.get("candidates") or []
        if not cands: raise RuntimeError(f"Empty completion: {data}")
        
        parts = (cands[0].get("content") or {}).get("parts") or []
        return "\n".join(p.get("text", "") for p in parts if "text" in p).strip()
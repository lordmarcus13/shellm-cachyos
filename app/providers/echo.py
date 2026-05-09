from __future__ import annotations
from typing import Iterable, Dict, Any

class EchoProvider:
    name = "echo"
    async def list_models(self) -> list[dict]:
        return [{"id":"echo/dev","name":"echo/dev"}]
    async def complete(self, messages: Iterable[Dict[str,str]], model: str | None = None, **gen_params: Any) -> str:
        last_user = ""
        for m in messages:
            if m.get("role") == "user":
                last_user = m.get("content","")
        return f"""```fish
# OBJECTIVE: {last_user}
echo 'Echo objective: {last_user}'
echo "//--OBJECTIVE_ACCOMPLISHED--//"
```"""

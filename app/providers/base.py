from __future__ import annotations
from typing import Iterable, Protocol, Dict, Any

class Provider(Protocol):
    name: str
    async def complete(self, messages: Iterable[Dict[str,str]], model: str | None = None, **gen_params: Any) -> str: ...

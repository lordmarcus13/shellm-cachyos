from __future__ import annotations
import asyncio, datetime as dt, re, uuid
from pathlib import Path
from typing import Dict, Any, Callable, Awaitable, Optional

from ..models import TaskRecord, TaskStatus
from ..config import settings
from .python_kernel import run_python
from .fish import run_fish
from ..logger import log_session_event, log_task_completion
from ..providers.base import Provider

SUCCESS_TOKEN_DEFAULT = "//--OBJECTIVE_ACCOMPLISHED--//"
PY_BLOCK_RE = re.compile(r"```python\s*(.*?)```", re.IGNORECASE | re.DOTALL)
FISH_BLOCK_RE = re.compile(r"```fish\s*(.*?)```", re.IGNORECASE | re.DOTALL)

class EventBus:
    def __init__(self) -> None:
        self._channels: Dict[str, asyncio.Queue] = {}
        self._history: Dict[str, list[Dict[str, Any]]] = {}
    
    def channel(self, task_id: str) -> asyncio.Queue:
        return self._channels.setdefault(task_id, asyncio.Queue())
    
    async def publish(self, task_id: str, event: Dict[str, Any]) -> None:
        event = dict(event)
        event.setdefault("ts", dt.datetime.utcnow().isoformat()+"Z")
        self._history.setdefault(task_id, []).append(event)
        if settings.log_enable: 
            log_session_event(task_id, event)
        await self.channel(task_id).put(event)
    
    def history(self, task_id: str) -> list[Dict[str, Any]]:
        return self._history.get(task_id, [])
    
    async def subscribe(self, task_id: str):
        q = self.channel(task_id)
        while True:
            yield await q.get()

class TaskManager:
    def __init__(self, provider_factory: Callable[..., Awaitable[object]], timeout_sec: int = 120) -> None:
        self.provider_factory = provider_factory
        self.timeout_sec = timeout_sec
        self.tasks: Dict[str, TaskRecord] = {}
        self._providers: Dict[str, Any] = {}
        self.bus = EventBus()

    def register_provider(self, task_id: str, provider: Any) -> None:
        self._providers[task_id] = provider

    async def create_task(self, *, objective: str, provider, model, success_token, dry_run: bool, system_prompt: str | None, gen_params: Dict[str,Any]) -> TaskRecord:
        task_id = str(uuid.uuid4())
        now = dt.datetime.utcnow()
        
        rec = TaskRecord(
            id=task_id, 
            created_at=now, 
            updated_at=now, 
            status=TaskStatus.pending, 
            provider=provider, 
            model=model, 
            objective=objective, 
            success_token=success_token or SUCCESS_TOKEN_DEFAULT, 
            dry_run=dry_run,
            system_prompt=system_prompt,
            gen_params=gen_params or {}
        )
        
        self.tasks[task_id] = rec
        asyncio.create_task(self._run_task(rec))
        return rec

    def get(self, task_id: str) -> TaskRecord | None: 
        return self.tasks.get(task_id)
    
    def get_history(self, task_id: str) -> list[Dict[str,Any]]: 
        return self.bus.history(task_id)

    async def cancel(self, task_id: str) -> bool:
        rec = self.tasks.get(task_id)
        if not rec: return False
        rec.status = TaskStatus.cancelled
        rec.updated_at = dt.datetime.utcnow()
        await self.bus.publish(rec.id, {"type":"status","status":rec.status})
        return True

    def _load_sys_prompt(self, rec: TaskRecord) -> str:
        base_prompt = "Return exactly one fenced ```fish``` or ```python``` block. Prefix with [CMD:FISH] or [CMD:PY] to route. Print success token."
        if rec.system_prompt: 
            base_prompt = rec.system_prompt
        else:
            p = Path(settings.system_prompt_path)
            if p.exists():
                try: base_prompt = p.read_text(encoding="utf-8")
                except Exception: pass
                
        injection = f"\n[DYNAMIC_RUNTIME_AWARENESS]\nCURRENT_OS: CachyOS Linux\nExecute using [CMD:FISH] or [CMD:PY] according to the task.\n[/DYNAMIC_RUNTIME_AWARENESS]\n\n"
        return injection + base_prompt

    async def _run_task(self, rec: TaskRecord) -> None:
        try:
            rec.status = TaskStatus.running
            rec.updated_at = dt.datetime.utcnow()
            await self.bus.publish(rec.id, {"type":"status","status":rec.status})
            
            gen_params = dict(rec.gen_params)
            max_cycles = int(gen_params.pop("max_cycles", 1))
            sys_prompt = self._load_sys_prompt(rec)
            messages = [{"role":"system","content":sys_prompt}, {"role":"user","content":rec.objective}]
            
            for cycle in range(1, max_cycles+1):
                await self.bus.publish(rec.id, {"type":"cycle","n":cycle})
                
                provider = self._providers.get(rec.id)
                if provider is None:
                    await asyncio.sleep(0.1)
                    provider = self._providers.get(rec.id)
                
                if provider is None:
                    await self.bus.publish(rec.id, {"type":"error","error":"Provider not registered for task"})
                    rec.status = TaskStatus.failed; break
                
                text = await provider.complete(messages, model=rec.model, **gen_params)
                await self.bus.publish(rec.id, {"type":"llm_text","text":text})
                
                # DTRM: Dynamic Tool Routing Mechanism
                py_match = PY_BLOCK_RE.search(text or "")
                fish_match = FISH_BLOCK_RE.search(text or "")
                
                mode = "unknown"
                payload = ""
                
                if "[CMD:PY]" in (text or "") or py_match:
                    mode = "python"
                    if py_match: payload = py_match.group(1).strip()
                elif "[CMD:FISH]" in (text or "") or fish_match:
                    mode = "fish"
                    if fish_match: payload = fish_match.group(1).strip()
                else:
                    if fish_match:
                        mode = "fish"; payload = fish_match.group(1).strip()
                    elif py_match: 
                        mode = "python"; payload = py_match.group(1).strip()
                
                if mode == "unknown" or not payload:
                    messages.append({"role":"assistant","content":text or ""})
                    messages.append({"role":"user","content":"No code block found. Provide ```fish``` or ```python``` block."})
                    continue
                
                if rec.dry_run:
                    rec.status = TaskStatus.succeeded
                    rec.updated_at = dt.datetime.utcnow()
                    await self.bus.publish(rec.id, {"type":"dry_run","payload":payload, "mode": mode})
                    break
                
                code_exit = 0
                out = ""
                err = ""

                if mode == "python":
                     code_exit, out, err = await run_python(payload, timeout_sec=settings.cmd_timeout_seconds)
                else:
                     code_exit, out, err = await run_fish(payload, timeout_sec=settings.cmd_timeout_seconds, elevated=False)

                await self.bus.publish(rec.id, {"type":"exec","mode":mode,"exit_code":code_exit,"stdout":out,"stderr":err})
                
                # Loose success check
                ok_token = (rec.success_token in text) or ("SUCCESS" in out) or ("OBJECTIVE_ACCOMPLISHED" in out)
                
                if code_exit == 0 and ok_token:
                    rec.status = TaskStatus.succeeded
                    rec.updated_at = dt.datetime.utcnow()
                    await self.bus.publish(rec.id, {"type":"status","status":rec.status})
                    break
                
                # Retry logic for elevation
                # Retry logic for elevation
                is_access_denied_fish = (mode == "fish") and ("Permission denied" in (err or "") or code_exit in (1, 126))
                is_access_denied_py = (mode == "python") and ("PermissionError" in (err or out or ""))
                
                if is_access_denied_fish or is_access_denied_py:
                    await self.bus.publish(rec.id, {"type":"retry","reason":"elevation"})
                    
                    if mode == "fish":
                        code2, out2, err2 = await run_fish(payload, timeout_sec=settings.cmd_timeout_seconds, elevated=True)
                        elevated_mode = "fish_elevated"
                    else:
                        code2, out2, err2 = await run_python(payload, timeout_sec=settings.cmd_timeout_seconds, elevated=True)
                        elevated_mode = "python_elevated"
                        
                    await self.bus.publish(rec.id, {"type":"exec","mode":elevated_mode,"exit_code":code2,"stdout":out2,"stderr":err2})
                    
                    if code2 == 0 and (ok_token or "OBJECTIVE_ACCOMPLISHED" in out2 or "SUCCESS" in out2):
                        rec.status = TaskStatus.succeeded
                        rec.updated_at = dt.datetime.utcnow()
                        await self.bus.publish(rec.id, {"type":"status","status":rec.status})
                        break
                    else:
                        messages.append({"role":"assistant","content":text})
                        messages.append({"role":"user","content":f"Elevation failed (Exit {code2}). stdout={out2[:300]} stderr={err2[:300]}"})
                else:
                    messages.append({"role":"assistant","content":text})
                    messages.append({"role":"user","content":f"Execution failed ({mode} Exit {code_exit}). stderr={err[:300]}"})

            if rec.status not in (TaskStatus.succeeded, TaskStatus.cancelled):
                rec.status = TaskStatus.failed
                rec.updated_at = dt.datetime.utcnow()
                await self.bus.publish(rec.id, {"type":"status","status":rec.status})
                
        except asyncio.CancelledError:
            rec.status = TaskStatus.cancelled
            rec.updated_at = dt.datetime.utcnow()
            await self.bus.publish(rec.id, {"type":"status","status":rec.status})
        except Exception as e:
            rec.status = TaskStatus.failed
            rec.updated_at = dt.datetime.utcnow()
            await self.bus.publish(rec.id, {"type":"error","error":str(e)})
            await self.bus.publish(rec.id, {"type":"status","status":rec.status})
        finally:
            if settings.log_enable:
                log_task_completion(rec, self.bus.history(rec.id))
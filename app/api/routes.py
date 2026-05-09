from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from ..config import settings
from ..models import CreateTaskRequest, TaskRecord, ProviderName, LogSource
from ..providers.openrouter import OpenRouterProvider
from ..providers.gemini import GeminiProvider
from ..providers.echo import EchoProvider
from ..runtime.task_manager import TaskManager
from ..logger import get_log_content

router = APIRouter()
# ARCHITECTURAL FIX: TaskManager instantiated without dummy factory abuse
manager = TaskManager(provider_factory=None, timeout_sec=settings.cmd_timeout_seconds)

def make_provider(name: ProviderName, openrouter_key: Optional[str], gemini_key: Optional[str]):
    if name == ProviderName.openrouter: 
        return OpenRouterProvider(openrouter_key or settings.openrouter_api_key or "")
    if name == ProviderName.gemini: 
        return GeminiProvider(gemini_key or settings.gemini_api_key or "")
    return EchoProvider()

@router.get("/models")
async def list_models(provider: ProviderName = Query(...), openrouter_key: Optional[str] = Query(None), gemini_key: Optional[str] = Query(None)):
    p = make_provider(provider, openrouter_key, gemini_key)
    if hasattr(p, "list_models"):
        data = await p.list_models()
        out = []
        if provider == ProviderName.openrouter:
            for m in data: out.append({"id": m.get("id") or m.get("name"), "name": m.get("name") or m.get("id")})
        elif provider == ProviderName.gemini:
            for m in data:
                mid = m.get("name","").split("/")[-1]
                out.append({"id": mid, "name": mid})
        else:
            for m in data: out.append({"id": m.get("id"), "name": m.get("name")})
        return {"models": out}
    return {"models": []}

@router.post("/tasks", response_model=TaskRecord)
async def create_task(req: CreateTaskRequest):
    provider = make_provider(req.provider, req.openrouter_key, req.gemini_key)
    objective = req.objective
    
    if req.inject_logs and req.log_source:
        log_content = get_log_content(req.log_source)
        if log_content:
            objective = f"<LOG_DATA log_source='{req.log_source.value}'>\n{log_content}\n</LOG_DATA>\n\n" + objective
            
    # Create the task
    rec = await manager.create_task(
        objective=objective, 
        provider=req.provider, 
        model=req.model, 
        success_token=req.success_token, 
        dry_run=req.dry_run, 
        system_prompt=req.system_prompt, 
        gen_params={
            "temperature": req.temperature, 
            "top_p": req.top_p, 
            "top_k": req.top_k, 
            "max_tokens": req.max_tokens, 
            "safety": req.safety, 
            "max_cycles": req.max_cycles
        }
    )
    
    # ARCHITECTURAL FIX: Use proper registration method instead of setattr
    manager.register_provider(rec.id, provider)
    
    return rec

@router.get("/tasks/{task_id}", response_model=TaskRecord)
async def get_task(task_id: str):
    rec = manager.get(task_id)
    if not rec: raise HTTPException(status_code=404, detail="Not found")
    return rec

@router.get("/tasks/{task_id}/events")
async def get_events(task_id: str, start: int | None = Query(None, alias="start"), end: int | None = Query(None, alias="end"), data_start: int | None = Query(None, alias="data-start"), data_end: int | None = Query(None, alias="data-end")):
    if start is None and data_start is not None: start = data_start
    if end is None and data_end is not None: end = data_end
    hist = manager.get_history(task_id)
    if not hist: return []
    n = len(hist)
    i0 = max(0, int(start)) if start is not None else 0
    i1 = min(n, int(end)) if end is not None else n
    if i0 >= i1: return []
    return JSONResponse(hist[i0:i1])

@router.get("/tasks/{task_id}/events.ndjson")
async def get_events_ndjson(task_id: str):
    hist = manager.get_history(task_id) or []
    return PlainTextResponse("".join(__import__("json").dumps(e, ensure_ascii=False) + "\n" for e in hist), media_type="application/x-ndjson")

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    ok = await manager.cancel(task_id)
    if not ok: raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}

@router.websocket("/ws/{task_id}")
async def task_ws(ws: WebSocket):
    await ws.accept()
    task_id = ws.path_params.get("task_id")
    if not task_id:
        await ws.close(code=1008)
        return
    try:
        async for event in manager.bus.subscribe(task_id):
            await ws.send_json(event)
    except WebSocketDisconnect: return
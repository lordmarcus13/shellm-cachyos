from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..models import TaskRecord, TaskStatus, ProviderName
from ..runtime.task_manager import TaskManager
from ..api.routes import manager as task_manager_instance
from .routes import make_provider
import datetime as dt

router = APIRouter()

class InjectionRequest(BaseModel):
    objective: str
    file_path: str
    provider: ProviderName = ProviderName.gemini # Default to high-intellect model
    model: str | None = None

@router.post("/inject", response_model=TaskRecord)
async def inject_task(req: InjectionRequest):
    """
    Headless Injection Endpoint ($P_{inject}$).
    Receives raw Data Objects ($D_{obj}$) + Query ($V_{query}$) from OS Hooks.
    """
    
    # Contextualize the objective with the file path
    final_objective = f"CONTEXT_FILE: {req.file_path}\n\nUSER_QUERY: {req.objective}"
    
    # Default provider setup (Using Gemini for context analysis)
    provider = make_provider(req.provider, None, None)
    
    # Spawn Task
    rec = await task_manager_instance.create_task(
        objective=final_objective,
        provider=req.provider,
        model=req.model,
        success_token="//--OBJECTIVE_ACCOMPLISHED--//",
        dry_run=False,
        system_prompt=None, # Use default system prompt
        gen_params={"max_cycles": 1}
    )
    
    task_manager_instance.register_provider(rec.id, provider)
    
    return rec

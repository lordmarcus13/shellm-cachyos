from __future__ import annotations
import datetime as dt
import enum
from typing import Literal, Any, Dict
from pydantic import BaseModel, Field

class ProviderName(str, enum.Enum):
    openrouter = "openrouter"
    gemini = "gemini"
    echo = "echo"

class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    cancelled = "cancelled"
    succeeded = "succeeded"
    failed = "failed"
    timed_out = "timed_out"

class LogSource(str, enum.Enum):
    session = "session"
    universal = "universal"
    successful = "successful"

class CreateTaskRequest(BaseModel):
    objective: str = Field(..., min_length=1)
    provider: ProviderName = Field(ProviderName.openrouter)
    model: str | None = Field(None)
    success_token: str = Field("//--OBJECTIVE_ACCOMPLISHED--//")
    dry_run: bool = Field(False)
    system_prompt: str | None = Field(None, description="Override system instruction")
    openrouter_key: str | None = None
    gemini_key: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_tokens: int | None = None
    safety: Any | None = None
    max_cycles: int = Field(1, ge=1, le=8)
    inject_logs: bool = Field(False, description="Toggle to inject log data into the prompt")
    log_source: LogSource | None = Field(None, description="Specify which log to inject")

class ProviderMessage(BaseModel):
    role: Literal["system","user","assistant","tool"]
    content: str

class TaskRecord(BaseModel):
    id: str
    created_at: dt.datetime
    updated_at: dt.datetime
    status: TaskStatus
    provider: ProviderName
    model: str | None
    objective: str
    success_token: str
    dry_run: bool = False
    # ARCHITECTURAL FIX: Store task-specific config in the record, preventing Manager State Pollution
    system_prompt: str | None = None
    gen_params: Dict[str, Any] = Field(default_factory=dict)
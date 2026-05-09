from __future__ import annotations
import os
import json
import logging
import logging.config
from typing import List, Dict, Any
from pathlib import Path
from .config import settings
from .models import TaskRecord, TaskStatus, LogSource

LOG_DIR = Path(settings.log_dir)
SESSION_LOG = LOG_DIR / settings.log_session_file
UNIVERSAL_LOG = LOG_DIR / settings.log_universal_file
SUCCESSFUL_LOG = LOG_DIR / settings.log_successful_file

def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    
    # CODE QUALITY FIX: Removed unconditional log deletion (SESSION_LOG.unlink)
    # CODE QUALITY FIX: Use dictConfig for robust configuration
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(message)s"
            }
        },
        "handlers": {
            "session_file": {
                "class": "logging.FileHandler",
                "filename": str(SESSION_LOG),
                "encoding": "utf-8",
                "formatter": "json",
                "level": "INFO",
                "mode": "a"  # Append mode
            },
            "universal_file": {
                "class": "logging.FileHandler",
                "filename": str(UNIVERSAL_LOG),
                "encoding": "utf-8",
                "formatter": "json",
                "level": "INFO",
                "mode": "a"
            },
            "successful_file": {
                "class": "logging.FileHandler",
                "filename": str(SUCCESSFUL_LOG),
                "encoding": "utf-8",
                "formatter": "json",
                "level": "INFO",
                "mode": "a"
            }
        },
        "loggers": {
            "session": {
                "handlers": ["session_file"],
                "level": "INFO",
                "propagate": False
            },
            "universal": {
                "handlers": ["universal_file"],
                "level": "INFO",
                "propagate": False
            },
            "successful": {
                "handlers": ["successful_file"],
                "level": "INFO",
                "propagate": False
            }
        }
    }
    logging.config.dictConfig(logging_config)

def log_session_event(task_id: str, event: dict):
    if not settings.log_enable: return
    try:
        log_entry = {"task_id": task_id, "ts": event.get("ts"), "type": event.get("type"), "event_data": event}
        logging.getLogger("session").info(json.dumps(log_entry, ensure_ascii=False))
    except Exception: pass

def log_task_completion(task_record: TaskRecord, history: List[Dict[str, Any]]):
    if not settings.log_enable: return
    try:
        request_payload = {
            "objective": task_record.objective, 
            "provider": task_record.provider.value, 
            "model": task_record.model, 
            "dry_run": task_record.dry_run
        }
        action_execution = [event for event in history if event.get("type") in ("llm_text", "exec")]
        terminal_io_state = {"final_status": task_record.status.value, "last_event": history[-1] if history else None}
        log_entry = {
            "task_id": task_record.id, 
            "request_payload": request_payload, 
            "action_execution": action_execution, 
            "terminal_io_state": terminal_io_state
        }
        log_str = json.dumps(log_entry, ensure_ascii=False)
        logging.getLogger("universal").info(log_str)
        if task_record.status == TaskStatus.succeeded:
            logging.getLogger("successful").info(log_str)
    except Exception: pass

def get_log_content(log_source: LogSource) -> str:
    if not settings.log_enable: return ""
    log_file_map = {LogSource.session: SESSION_LOG, LogSource.universal: UNIVERSAL_LOG, LogSource.successful: SUCCESSFUL_LOG}
    file_path = log_file_map.get(log_source)
    if not file_path or not file_path.exists(): return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f: return f.read()
    except Exception: return ""
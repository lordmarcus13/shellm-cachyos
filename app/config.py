from __future__ import annotations
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_host: str = Field("127.0.0.1", alias="APP_HOST")
    app_port: int = Field(8080, alias="APP_PORT")
    openrouter_api_key: str | None = Field(None, alias="OPENROUTER_API_KEY")
    gemini_api_key: str | None = Field(None, alias="GEMINI_API_KEY")
    system_prompt_path: str = Field("app/system_instruction.md", alias="SYSTEM_PROMPT_PATH")
    cmd_timeout_seconds: int = Field(120, alias="CMD_TIMEOUT_SECONDS")
    log_enable: bool = Field(True, alias="LOG_ENABLE")
    log_dir: str = Field("logs", alias="LOG_DIR")
    log_session_file: str = Field("session.log.jsonl", alias="LOG_SESSION_FILE")
    log_universal_file: str = Field("universal.log.jsonl", alias="LOG_UNIVERSAL_FILE")
    log_successful_file: str = Field("successful.log.jsonl", alias="LOG_SUCCESSFUL_FILE")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

settings = Settings()

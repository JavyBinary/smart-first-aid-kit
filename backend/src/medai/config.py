"""Configuration models and loader for MedAI backend."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AuthConfig",
    "AuthRateLimitConfig",
    "Config",
    "DatabaseConfig",
    "LiteLLMProviderConfig",
    "LoggingConfig",
    "RedisConfig",
    "load_config",
]

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["human", "json"]


class DatabaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str = Field(
        default="postgresql+asyncpg://medai:medai@localhost:5432/medai",
        description="SQLAlchemy asyncpg connection URL",
    )


class RedisConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for session storage and rate limiting",
    )


class AuthRateLimitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    login_failures: int = Field(default=5, ge=1)
    login_failure_window_seconds: int = Field(default=900, ge=1)
    login_per_ip: int = Field(default=30, ge=1)
    login_per_ip_window_seconds: int = Field(default=60, ge=1)
    register_per_ip: int = Field(default=10, ge=1)
    register_per_ip_window_seconds: int = Field(default=3600, ge=1)


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    jwt_secret: str = Field(
        default="dev-insecure-jwt-secret-replace-in-production-min32chars",
        min_length=16,
    )
    access_ttl_seconds: int = Field(default=900, ge=60)
    refresh_ttl_seconds: int = Field(default=2592000, ge=3600)
    cookie_secure: bool = False
    rate_limit: AuthRateLimitConfig = Field(default_factory=AuthRateLimitConfig)


class LiteLLMProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(default="gpt-4o-mini")
    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: float = Field(default=60.0, gt=0)
    num_retries: int = Field(default=2, ge=0)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    thinking: bool = False


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    level: LogLevel = "INFO"
    format: LogFormat = "human"


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    database: DatabaseConfig
    redis: RedisConfig
    auth: AuthConfig
    llm: LiteLLMProviderConfig = Field(default_factory=LiteLLMProviderConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(environ: Mapping[str, str] | None = None) -> Config:
    source = os.environ if environ is None else environ

    database_values: dict[str, Any] = {}
    if "DATABASE_URL" in source and source["DATABASE_URL"].strip():
        database_values["url"] = source["DATABASE_URL"].strip()

    redis_values: dict[str, Any] = {}
    if "REDIS_URL" in source and source["REDIS_URL"].strip():
        redis_values["url"] = source["REDIS_URL"].strip()

    auth_values: dict[str, Any] = {}
    for env_name, field_name in (
        ("AUTH_JWT_SECRET", "jwt_secret"),
        ("AUTH_ACCESS_TTL_SECONDS", "access_ttl_seconds"),
        ("AUTH_REFRESH_TTL_SECONDS", "refresh_ttl_seconds"),
        ("AUTH_COOKIE_SECURE", "cookie_secure"),
    ):
        if env_name in source and source[env_name].strip():
            raw_val = source[env_name].strip()
            if field_name == "cookie_secure":
                auth_values[field_name] = raw_val.lower() in ("true", "1", "yes")
            elif field_name in ("access_ttl_seconds", "refresh_ttl_seconds"):
                auth_values[field_name] = int(raw_val)
            else:
                auth_values[field_name] = raw_val

    rate_limit_values: dict[str, Any] = {}
    for env_name, field_name in (
        ("AUTH_LOGIN_MAX_FAILURES", "login_failures"),
        ("AUTH_LOGIN_FAILURE_WINDOW_SECONDS", "login_failure_window_seconds"),
        ("AUTH_LOGIN_MAX_PER_IP", "login_per_ip"),
        ("AUTH_LOGIN_PER_IP_WINDOW_SECONDS", "login_per_ip_window_seconds"),
        ("AUTH_REGISTER_MAX_PER_IP", "register_per_ip"),
        ("AUTH_REGISTER_PER_IP_WINDOW_SECONDS", "register_per_ip_window_seconds"),
    ):
        if env_name in source and source[env_name].strip():
            rate_limit_values[field_name] = int(source[env_name].strip())
    if rate_limit_values:
        auth_values["rate_limit"] = rate_limit_values

    llm_values: dict[str, Any] = {}
    for env_name, field_name in (
        ("LLM_MODEL", "model"),
        ("LLM_API_KEY", "api_key"),
        ("LLM_BASE_URL", "base_url"),
        ("LLM_TIMEOUT_SECONDS", "timeout_seconds"),
        ("LLM_NUM_RETRIES", "num_retries"),
        ("LLM_TEMPERATURE", "temperature"),
        ("LLM_THINKING", "thinking"),
    ):
        if env_name in source and source[env_name].strip():
            raw_val = source[env_name].strip()
            if field_name == "timeout_seconds":
                llm_values[field_name] = float(raw_val)
            elif field_name == "num_retries":
                llm_values[field_name] = int(raw_val)
            elif field_name == "temperature":
                llm_values[field_name] = float(raw_val)
            elif field_name == "thinking":
                llm_values[field_name] = raw_val.lower() in ("true", "1", "yes")
            else:
                llm_values[field_name] = raw_val

    logging_values: dict[str, Any] = {}
    for env_name, field_name in (
        ("LOG_LEVEL", "level"),
        ("LOG_FORMAT", "format"),
    ):
        if env_name in source and source[env_name].strip():
            logging_values[field_name] = source[env_name].strip()

    return Config(
        database=DatabaseConfig.model_validate(database_values),
        redis=RedisConfig.model_validate(redis_values),
        auth=AuthConfig.model_validate(auth_values),
        llm=LiteLLMProviderConfig.model_validate(llm_values),
        logging=LoggingConfig.model_validate(logging_values),
    )

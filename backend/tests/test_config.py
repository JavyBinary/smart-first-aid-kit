"""Unit tests for MedAI configuration models and loader."""

import pytest
from pydantic import ValidationError

from medai.config import (
    Config,
    LoggingConfig,
    load_config,
)


def test_load_config_defaults() -> None:
    config = load_config({})
    assert isinstance(config, Config)
    assert config.database.url.startswith("postgresql+asyncpg://")
    assert config.redis.url.startswith("redis://")
    assert config.auth.access_ttl_seconds == 900
    assert config.auth.refresh_ttl_seconds == 2592000
    assert not config.auth.cookie_secure
    assert config.llm.model == "gpt-4o-mini"
    assert config.logging.level == "INFO"
    assert config.logging.format == "human"


def test_load_config_custom_env() -> None:
    custom_env = {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@dbhost:5432/medtest",
        "REDIS_URL": "redis://redishost:6379/2",
        "AUTH_JWT_SECRET": "test_super_secret_key_minimum_length_32_chars!",
        "AUTH_ACCESS_TTL_SECONDS": "300",
        "AUTH_COOKIE_SECURE": "true",
        "LLM_MODEL": "openai/gpt-4o",
        "LLM_TEMPERATURE": "0.5",
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "json",
    }
    config = load_config(custom_env)
    assert config.database.url == "postgresql+asyncpg://user:pass@dbhost:5432/medtest"
    assert config.redis.url == "redis://redishost:6379/2"
    assert config.auth.jwt_secret == "test_super_secret_key_minimum_length_32_chars!"
    assert config.auth.access_ttl_seconds == 300
    assert config.auth.cookie_secure is True
    assert config.llm.model == "openai/gpt-4o"
    assert config.llm.temperature == 0.5
    assert config.logging.level == "DEBUG"
    assert config.logging.format == "json"


def test_config_models_frozen() -> None:
    config = load_config({})
    with pytest.raises(ValidationError):
        config.logging.level = "DEBUG"  # type: ignore[misc]


def test_config_models_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        LoggingConfig.model_validate({"level": "INFO", "unknown_extra_param": 123})

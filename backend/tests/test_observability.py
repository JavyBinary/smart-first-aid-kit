"""Unit tests for MedAI structured observability, context binding, and request middleware."""

import json
import logging

import httpx
import pytest

from medai.main import create_app
from medai.observability import (
    _CONTEXT,
    EventFormatter,
    bind_context,
    log_event,
    utc_now,
)


def test_utc_now_format() -> None:
    now_str = utc_now()
    assert now_str.endswith("Z")
    assert "T" in now_str


def test_bind_context_lifecycle() -> None:
    assert _CONTEXT["request_id"].get() is None
    with bind_context(request_id="req-123", dialog_id="dlg-456"):
        assert _CONTEXT["request_id"].get() == "req-123"
        assert _CONTEXT["dialog_id"].get() == "dlg-456"
    assert _CONTEXT["request_id"].get() is None
    assert _CONTEXT["dialog_id"].get() is None


def test_bind_context_invalid_key() -> None:
    with pytest.raises(ValueError, match="Unsupported log context field"):
        with bind_context(invalid_key="test"):  # type: ignore[call-arg]
            pass


def test_log_event_safe_and_unsafe_fields() -> None:
    logger = logging.getLogger("test_obs")
    logger.setLevel(logging.INFO)

    # Safe field should succeed
    with bind_context(request_id="req-safe"):
        log_event(logger, logging.INFO, "test.event", duration_ms=12.5, status_code=200)

    # Unsafe / unwhitelisted field must raise ValueError to prevent leaks
    with pytest.raises(ValueError, match="Unsupported log event field"):
        log_event(logger, logging.INFO, "test.leak", password_raw="secret123")


def test_event_formatter_human_and_json() -> None:
    record = logging.LogRecord(
        name="medai.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test_event",
        args=(),
        exc_info=None,
    )
    record.created = 1700000000.0
    record.event = "test.event"  # type: ignore[attr-defined]
    record.log_fields = {"duration_ms": 42.0, "status_code": 200}  # type: ignore[attr-defined]

    # Human formatter
    formatter_human = EventFormatter("human")
    output_human = formatter_human.format(record)
    assert 'event="test.event"' in output_human
    assert "duration_ms=42.0" in output_human

    # JSON formatter
    formatter_json = EventFormatter("json")
    output_json = formatter_json.format(record)
    data = json.loads(output_json)
    assert data["event"] == "test.event"
    assert data["duration_ms"] == 42.0
    assert data["status_code"] == 200
    assert data["level"] == "INFO"


@pytest.mark.asyncio
async def test_request_log_middleware_and_health_endpoint() -> None:
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "medai-backend"
        assert data["version"] == "0.1.0"
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 10

"""HTTP origin / CSRF protection middleware for browser state-changing endpoints."""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

__all__ = ["ForbiddenOriginMiddleware"]

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class ForbiddenOriginMiddleware:
    """Reject cross-site unsafe browser requests when Sec-Fetch-Site is 'cross-site'."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            method = scope.get("method", "GET").upper()
            if method in _UNSAFE_METHODS:
                headers = {
                    k.decode("latin-1").lower(): v.decode("latin-1").lower()
                    for k, v in scope.get("headers", ())
                }
                sec_fetch_site = headers.get("sec-fetch-site", "").strip()
                if sec_fetch_site == "cross-site":
                    resp = JSONResponse(
                        {"detail": "Cross-site requests are forbidden."},
                        status_code=403,
                    )
                    await resp(scope, receive, send)
                    return
        await self._app(scope, receive, send)

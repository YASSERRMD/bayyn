"""Request-ID middleware: generates/forwards X-Request-ID and stores it in context."""
from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import logging

REQUEST_ID_HEADER = "X-Request-ID"
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_var.get()


logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique X-Request-ID to every request/response and log access lines."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = _request_id_var.set(req_id)

        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            raise
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            _request_id_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = req_id
        logger.info(
            "request completed",
            extra={
                "request_id": req_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 1),
            },
        )
        return response

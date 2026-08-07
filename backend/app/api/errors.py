"""Uniform error envelope and the global exception handlers that produce it.

Every non-2xx response leaves the API in one shape::

    {"error": {"code", "message", "fields": [{"path", "message"}], "request_id"?}}

so the frontend has a single contract to parse (see the ApiError parser in
frontend/src/lib/api/client.ts). The handlers translate FastAPI's three native
failure modes — request validation, a raised HTTPException, and an uncaught
exception — into that shape.
"""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import messages
from app.exceptions import ProfileNotFoundError, ProjectOwnershipError

logger = logging.getLogger(__name__)

GENERIC_MESSAGE = "Something went wrong on our end. Please try again."
VALIDATION_MESSAGE = "Some details need fixing."

# Machine-readable code per status, so the client can branch without parsing prose.
_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "upstream_error",
    503: "service_unavailable",
}

# Leading location segments Pydantic adds that name the request part, not the field.
_LOC_PREFIXES = {"body", "query", "path", "header", "cookie"}


def _code_for_status(status_code: int) -> str:
    return _STATUS_CODES.get(status_code, "error")


def _humanize(msg: str) -> str:
    """Strip Pydantic's 'Value error, ' prefix from custom ValueError messages."""
    return msg.removeprefix("Value error, ")


def _field_from_error(error: dict[str, Any]) -> dict[str, Any]:
    loc = list(error.get("loc", ()))
    if loc and loc[0] in _LOC_PREFIXES:
        loc = loc[1:]
    return {"path": loc, "message": _humanize(str(error.get("msg", "is invalid")))}


def _envelope(
    status_code: int,
    *,
    message: str,
    code: str | None = None,
    fields: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code or _code_for_status(status_code),
        "message": message,
        "fields": fields or [],
    }
    if request_id is not None:
        error["request_id"] = request_id
    return JSONResponse(status_code=status_code, content={"error": error}, headers=headers)


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Surface only loc + msg. Pydantic's 'input'/'ctx' can carry the raw submitted
    # value (PII) and non-JSON-serializable objects — never echo them back.
    fields = [_field_from_error(error) for error in exc.errors()]
    return _envelope(422, code="validation_error", message=VALIDATION_MESSAGE, fields=fields)


async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Routes raise HTTPException with a string detail; wrap it in the envelope,
    # preserving any headers (e.g. WWW-Authenticate on a 401).
    message = exc.detail if isinstance(exc.detail, str) else GENERIC_MESSAGE
    return _envelope(exc.status_code, message=message, headers=exc.headers)


async def _profile_not_found_handler(request: Request, exc: ProfileNotFoundError) -> JSONResponse:
    return _envelope(404, code="profile_not_found", message=str(exc))


async def _project_ownership_handler(request: Request, exc: ProjectOwnershipError) -> JSONResponse:
    # Point at the submitted row so the client can map it back to the visible
    # editor row even when it filtered blank drafts out of the request.
    return _envelope(
        409,
        code="projects_stale",
        message=messages.PROJECTS_STALE,
        fields=[
            {
                "path": ["projects", exc.row_index],
                "message": messages.PROJECTS_STALE,
            }
        ],
    )


def _unhandled_response(request: Request, exc: Exception) -> JSONResponse:
    # A request_id lets support correlate a user's failure with the server log
    # without leaking internals (stack, exception text) into the response.
    request_id = uuid.uuid4().hex
    logger.exception("Unhandled error [request_id=%s] on %s", request_id, request.url.path)
    return _envelope(500, code="internal_error", message=GENERIC_MESSAGE, request_id=request_id)


class UnhandledExceptionMiddleware:
    """Convert an uncaught exception into the envelope from *inside* the CORS
    middleware, so the 500 still carries Access-Control-Allow-Origin (and the
    request_id actually reaches the browser).

    The bare ``add_exception_handler(Exception)`` below cannot do this: Starlette
    pins the 500 handler to the outermost ServerErrorMiddleware, which runs
    outside CORS — the browser then sees a CORS failure and loses the response.
    Installed before CORSMiddleware so CORS wraps it.

    A pure-ASGI middleware (not BaseHTTPMiddleware) so successful responses,
    including streaming ones, pass through untouched; it only steps in when an
    exception propagates before any response bytes were sent.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:  # noqa: BLE001 — deliberate outermost boundary
            # If bytes were already sent we can't replace the response; re-raise
            # and let the server abort the connection rather than corrupt it.
            if response_started:
                raise
            await _unhandled_response(Request(scope, receive), exc)(scope, receive, send)


def register_error_handlers(app: FastAPI) -> None:
    """Wire the envelope handlers onto the app. Call once at startup, before the
    CORS middleware is added so CORS remains the outermost user middleware."""
    app.add_middleware(UnhandledExceptionMiddleware)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.add_exception_handler(ProfileNotFoundError, _profile_not_found_handler)
    app.add_exception_handler(ProjectOwnershipError, _project_ownership_handler)
    # Fallback if the middleware itself fails; runs in ServerErrorMiddleware.
    app.add_exception_handler(Exception, _unhandled_response)

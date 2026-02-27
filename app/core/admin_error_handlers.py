"""Human-friendly exception handlers for the fastapi-amis-admin sub-application.

Problem
-------
fastapi-amis-admin registers two handlers on its internal FastAPI sub-app:

  RequestValidationError → msg = "Request parameter validation exception"
  Exception              → msg = "Internal server exception"

AMIS only surfaces the ``msg`` field in its toast notification; the ``errors``
array that these handlers also return is never shown to the admin user.  The
result is generic, actionless feedback regardless of what actually went wrong.

Solution
--------
These handlers are registered on ``admin_site.fastapi`` *after* mount_app so
they shadow the built-in ones (Starlette stores handlers in a dict keyed by
exception class — last write wins).

  1. ``friendly_validation_handler``   — RequestValidationError (422)
     Builds "field: reason" pairs from Pydantic v2 error objects and joins them
     into a single readable sentence shown in the toast.

  2. ``friendly_integrity_error_handler`` — SQLAlchemy IntegrityError
     Maps common PostgreSQL constraint names to plain English sentences.
     Registered before the generic handler so it matches first (MRO lookup).

  3. ``friendly_server_error_handler`` — Exception (catch-all)
     Shows a safe generic message while re-raising so the error is still logged
     by the request-logging middleware (identical to the built-in behaviour).
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_amis_admin.admin.handlers import make_error_response
from fastapi_amis_admin.crud import BaseApiOut
from sqlalchemy.exc import IntegrityError
from starlette.status import (
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

logger = logging.getLogger("pantry_mate.admin")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _amis_error_response(status: int, msg: str) -> JSONResponse:
    """Return a plain JSONResponse (no re-raise) with BaseApiOut envelope."""
    return JSONResponse(
        status_code=status,
        content=BaseApiOut(status=status, msg=msg).dict(),
    )


def _loc_to_field(loc: tuple) -> str:
    """Convert a Pydantic error ``loc`` tuple to a readable field name.

    Examples
    --------
    ("body", "email")              → "email"
    ("body", "user", "full_name")  → "user → full_name"
    ("body", 0, "name")            → "item 0 → name"
    """
    # Drop transport-layer prefixes that mean nothing to an admin user
    skip = {"body", "query", "path", "header", "cookie"}
    parts = []
    for segment in loc:
        if isinstance(segment, int):
            parts.append(f"item {segment}")
        elif str(segment) not in skip:
            parts.append(str(segment))
    return " → ".join(parts) if parts else "input"


# ── Handlers ──────────────────────────────────────────────────────────────────

async def friendly_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic v2 validation errors into a readable admin toast message.

    Each error is formatted as  "field": reason  and joined with semicolons.

    Single error  →  Validation error — "email": Value required
    Many errors   →  3 validation errors — "email": Value required;
                      "full_name": String should have at most 255 characters; ...
    """
    errors = exc.errors()
    parts: list[str] = []

    for err in errors:
        field    = _loc_to_field(err.get("loc", ()))
        raw_msg  = err.get("msg", "Invalid value")
        # Pydantic v2 prefixes validator messages with "Value error, " — strip it
        clean_msg = raw_msg.removeprefix("Value error, ")
        parts.append(f'"{field}": {clean_msg}')

    if not parts:
        friendly = "Invalid request — please check your input."
    elif len(parts) == 1:
        friendly = f"Validation error — {parts[0]}"
    else:
        friendly = f"{len(parts)} validation errors — " + "; ".join(parts)

    logger.warning("Admin form validation error on %s: %s", request.url.path, friendly)
    return _amis_error_response(HTTP_422_UNPROCESSABLE_ENTITY, friendly)


async def friendly_integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """Convert a PostgreSQL constraint violation into plain English.

    Common cases handled:
    - unique / duplicate  → duplicate value warning
    - foreign key         → related record missing / in use
    - not null            → required field missing
    - check               → value out of allowed range
    """
    orig = str(getattr(exc, "orig", exc)).lower()

    if "unique" in orig or "duplicate" in orig:
        msg = "A record with this value already exists — check for duplicate entries."
    elif "foreign key" in orig:
        msg = (
            "This record is linked to another and cannot be modified or removed, "
            "or the referenced record does not exist."
        )
    elif "not null" in orig or "null value" in orig:
        msg = "A required field is missing — please fill in all required fields."
    elif "check" in orig:
        msg = "A field value is outside the allowed range or does not meet constraints."
    else:
        msg = "A database constraint was violated — please check your input."

    logger.warning(
        "Admin IntegrityError on %s: %s", request.url.path, exc.orig or exc
    )
    return _amis_error_response(HTTP_409_CONFLICT, msg)


async def friendly_server_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler: show a safe generic message and re-raise for logging.

    The re-raise is forwarded via ``make_error_response`` / ``JSONResponseWithException``
    which is the same pattern used by the built-in handler — it preserves logging
    from the request middleware without crashing the response pipeline.
    """
    logger.exception("Unhandled exception in admin on %s", request.url.path)
    return make_error_response(
        status=HTTP_500_INTERNAL_SERVER_ERROR,
        msg="An unexpected error occurred. Please try again or contact support.",
        exc=exc,
    )

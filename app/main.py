import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware
from app.db.session import engine

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("pantry_mate")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    # Seed default categories (idempotent — safe on every restart)
    # Run all seeders (idempotent & ordered)
    from app.db.seeders.main_seeder import run_all_seeders
    await run_all_seeders()

    # Launch in-process expiry notification loop (every hour)
    from app.tasks.expiry_notifications import schedule_daily
    _task = asyncio.create_task(schedule_daily(interval_seconds=3600))
    logger.info("Expiry notification scheduler started")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    _task.cancel()
    await engine.dispose()
    logger.info("Application shut down cleanly")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade pantry & recipe management API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# ── API Routes ────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix="/api/v1")

# ── Admin Panel ───────────────────────────────────────────────────────────────

from app.admin.site import admin_site
import app.admin.views as _admin_views  # noqa: F401 — registers all admin views

admin_site.mount_app(app)

# ── Override admin error handlers with user-friendly messages ─────────────────
# mount_app registers generic handlers on admin_site.fastapi (the sub-app).
# Re-registering after mount shadows them — Starlette stores handlers in a dict
# keyed by exception class, so the last write for each type wins.
from fastapi.exceptions import RequestValidationError  # noqa: E402
from sqlalchemy.exc import IntegrityError              # noqa: E402
from app.core.admin_error_handlers import (            # noqa: E402
    friendly_integrity_error_handler,
    friendly_server_error_handler,
    friendly_validation_handler,
)

admin_site.fastapi.add_exception_handler(RequestValidationError, friendly_validation_handler)
admin_site.fastapi.add_exception_handler(IntegrityError,         friendly_integrity_error_handler)
admin_site.fastapi.add_exception_handler(Exception,              friendly_server_error_handler)

# ── Global API exception handlers ────────────────────────────────────────────
# These apply to all /api/v1/* routes (main app, not the admin sub-app).
# They return structured {"success": false, "error_code": ..., "message": ...}
# instead of FastAPI's default {"detail": ...} envelope.

from fastapi.exceptions import RequestValidationError as _RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse as _JSONResponse                         # noqa: E402
from app.core.exceptions import AppException                                        # noqa: E402


@app.exception_handler(AppException)
async def _app_exception_handler(request, exc: AppException) -> _JSONResponse:
    return _JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(_RequestValidationError)
async def _validation_exception_handler(request, exc: _RequestValidationError) -> _JSONResponse:
    errors = exc.errors()
    parts: list[str] = []
    for err in errors:
        loc  = " → ".join(
            str(s) for s in err.get("loc", ()) if s not in ("body", "query", "path")
        )
        msg  = err.get("msg", "invalid value").removeprefix("Value error, ")
        parts.append(f'"{loc or "input"}": {msg}')
    message = (
        f"{len(parts)} validation errors — " + "; ".join(parts)
        if len(parts) != 1
        else f"Validation error — {parts[0]}"
    )
    return _JSONResponse(
        status_code=422,
        content={"success": False, "error_code": "VALIDATION_ERROR", "message": message},
    )


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}

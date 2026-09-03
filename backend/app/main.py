"""FastAPI application factory and entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.api.routes import system as system_routes
from app.core.config import settings
from app.core.context import get_request_id
from app.core.errors import (
    AppError,
    DatabaseError,
    ErrorCode,
    NotFoundError,
    ValidationError,
)
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.observability import configure_opik, flush_opik

logger = get_logger("app.main")

DESCRIPTION = """\
Generate audience-specific marketing copy for Email, Mobile and SMS through a
six-stage AI workflow: data extraction, web search grounding, copy generation,
repetition fix, CTA optimisation, and output parsing.
"""


def _assert_schema_current(engine) -> None:
    """Fail fast when an existing database predates a model change.

    ``create_all`` adds missing tables but never alters existing ones, so a new
    column on an old database surfaces as an opaque "no such column" error deep
    in the first query. Detect it here and say exactly how to fix it.
    """
    from sqlalchemy import inspect

    from app.database.base import Base

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    drift: list[str] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        actual = {column["name"] for column in inspector.get_columns(table.name)}
        missing = [column.name for column in table.columns if column.name not in actual]
        drift.extend(f"{table.name}.{name}" for name in missing)

    if drift:
        raise RuntimeError(
            "The database schema is out of date; these columns are missing: "
            + ", ".join(sorted(drift))
            + ". Run 'alembic upgrade head' to migrate. If the database was created by "
            "AUTO_CREATE_TABLES rather than Alembic, first run "
            "'alembic stamp 0001_initial'. Deleting the database file also works, but "
            "discards all existing data."
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    configure_opik()
    logger.info(
        "starting application",
        extra={
            "app_env": settings.app_env,
            "ai_provider": settings.ai_provider,
            "grounding_enabled": settings.grounding_enabled,
        },
    )

    if settings.auto_create_tables:
        # Convenience for local development. Deployments run Alembic instead.
        import app.models  # noqa: F401 - registers the tables
        from app.database.base import Base
        from app.database.session import engine

        Base.metadata.create_all(bind=engine)
        logger.info("database tables ensured")
        _assert_schema_current(engine)

    from app.database.session import session_scope

    if settings.seed_on_startup:
        from app.database.seed import seed_all

        with session_scope() as session:
            seed_all(session)

    # A generation runs as an in-process background task, so any run still open
    # belongs to a process that no longer exists.
    from app.services.generation_service import fail_interrupted_generations

    with session_scope() as session:
        fail_interrupted_generations(session)

    yield
    flush_opik()
    logger.info("shutting down application")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)

    if settings.image_generation_enabled:
        from pathlib import Path

        media_dir = Path(settings.media_dir)
        media_dir.mkdir(parents=True, exist_ok=True)
        app.mount(settings.media_url_prefix, StaticFiles(directory=media_dir), name="media")

    app.include_router(system_routes.router)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api": settings.api_prefix,
        }

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Map every exception class onto the standard error envelope (§16)."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        headers = {}
        retry_after = getattr(exc, "retry_after", None)
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_payload(get_request_id()),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())[1:]) or "body",
                "message": error.get("msg", "Invalid value."),
            }
            for error in exc.errors()
        ]
        error = ValidationError("Please correct the highlighted fields.", details=details)
        return JSONResponse(
            status_code=error.status_code, content=error.to_payload(get_request_id())
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            error: AppError = NotFoundError()
        else:
            error = AppError(
                str(exc.detail),
                code=ErrorCode.INTERNAL_ERROR if exc.status_code >= 500 else "HTTP_ERROR",
                status_code=exc.status_code,
            )
        return JSONResponse(
            status_code=error.status_code,
            content=error.to_payload(get_request_id()),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("database error")
        error = DatabaseError()
        return JSONResponse(
            status_code=error.status_code, content=error.to_payload(get_request_id())
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        # Stack traces stay in the log; the client only sees a generic message.
        logger.exception("unhandled application error")
        error = AppError()
        return JSONResponse(
            status_code=error.status_code, content=error.to_payload(get_request_id())
        )


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
    )

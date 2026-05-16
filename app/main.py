from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes_applications import router as applications_router
from app.api.routes_data_folder import router as data_folder_router
from app.api.routes_health import router as health_router
from app.api.routes_people import router as people_router
from app.api.routes_resumes import router as resumes_router
from app.api.routes_settings import router as settings_router
from app.api.routes_setup import router as setup_router
from app.core.errors import AppError
from app.db.session import (
    create_session_factory,
    create_sqlite_engine,
    initialise_database,
)
from app.secrets.openai_key import OpenAISecretService, build_openai_secret_service
from app.settings.service import SettingsService
from app.storage.bootstrap import bootstrap_app_data_dirs
from app.web.routes import router as web_router
from app.web.templating import templates

logger = logging.getLogger(__name__)

_SETUP_GATE_EXEMPT_PREFIXES = (
    "/setup",
    "/settings",
    "/data-folder",
    "/profiles",
    "/resumes",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
)


def create_app(*, openai_secret_service: OpenAISecretService | None = None) -> FastAPI:
    app = FastAPI(title="AI JOB APPLICATION ASSISTANT", version="0.3.0")
    paths = bootstrap_app_data_dirs()
    engine = create_sqlite_engine(paths.database_file)
    initialise_database(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        SettingsService(session).ensure_defaults()

    app.state.app_data_paths = paths
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.openai_secret_service = (
        openai_secret_service or build_openai_secret_service()
    )

    @app.middleware("http")
    async def setup_gate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if (
            path == "/"
            or path.startswith(_SETUP_GATE_EXEMPT_PREFIXES)
            or path.startswith("/applications")
        ):
            return await call_next(request)
        return await call_next(request)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> Response:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": exc.title,
                "message": exc.message,
                "status_code": exc.status_code,
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> Response:
        message = str(exc.detail or "The requested action could not be completed.")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": "Request error",
                "message": message,
                "status_code": exc.status_code,
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> Response:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": "Request error",
                "message": str(exc.detail or "The requested page could not be found."),
                "status_code": exc.status_code,
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> Response:
        logger.exception("Unhandled application error", exc_info=exc)
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": "Unexpected error",
                "message": "Something went wrong. Please return to a safe page and "
                "try again.",
                "status_code": 500,
            },
            status_code=500,
        )

    app.include_router(health_router)
    app.include_router(web_router)
    app.include_router(setup_router)
    app.include_router(settings_router)
    app.include_router(data_folder_router)
    app.include_router(people_router)
    app.include_router(resumes_router)
    app.include_router(applications_router)
    return app


app = create_app()

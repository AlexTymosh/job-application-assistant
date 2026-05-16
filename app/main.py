from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.api.routes_applications import router as applications_router
from app.api.routes_data_folder import router as data_folder_router
from app.api.routes_health import router as health_router
from app.api.routes_people import router as people_router
from app.api.routes_resumes import router as resumes_router
from app.api.routes_settings import router as settings_router
from app.api.routes_setup import router as setup_router
from app.db.session import (
    create_session_factory,
    create_sqlite_engine,
    initialise_database,
)
from app.secrets.openai_key import OpenAISecretService, build_openai_secret_service
from app.settings.service import SettingsService
from app.storage.bootstrap import bootstrap_app_data_dirs
from app.web.routes import router as web_router

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
    app = FastAPI(title="Local Resume Builder and AI Tailoring", version="0.2.0")
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

from __future__ import annotations

import sqlite3
from collections.abc import Awaitable, Callable

import yaml
from fastapi import FastAPI, Request, status
from fastapi.responses import RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes_applications import router as applications_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_data_folder import router as data_folder_router
from app.api.routes_health import router as health_router
from app.api.routes_profiles import router as profiles_router
from app.api.routes_review import router as review_router
from app.api.routes_settings import router as settings_router
from app.api.routes_setup import router as setup_router
from app.core.config import ProjectConfig
from app.db.session import create_session_factory, create_sqlite_engine
from app.runtime import refresh_runtime_state
from app.secrets.openai_key import OpenAISecretService, build_openai_secret_service
from app.settings.init import initialise_app_settings_storage
from app.settings.service import load_effective_project_config
from app.setup.init import initialise_setup_state
from app.setup.service import SetupStatusService
from app.storage.bootstrap import bootstrap_app_data_dirs
from app.web.routes import router as web_router

_SETUP_GATE_EXEMPT_PATHS = {
    "/setup",
    "/setup/",
    "/settings",
    "/settings/",
    "/data-folder",
    "/data-folder/",
    "/health/live",
    "/health/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}

_EXPECTED_STARTUP_SETUP_EXCEPTIONS = (
    FileNotFoundError,
    ValueError,
    ValidationError,
    OSError,
    sqlite3.DatabaseError,
    SQLAlchemyError,
    yaml.YAMLError,
)


def create_app(
    config: ProjectConfig | None = None,
    *,
    openai_secret_service: OpenAISecretService | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Local Job Application Assistant",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app_data_paths = bootstrap_app_data_dirs()
    app_settings_service = None
    try:
        app_settings_service = initialise_app_settings_storage(app_data_paths)
    except _EXPECTED_STARTUP_SETUP_EXCEPTIONS:
        app_settings_service = None

    startup_config = config
    if startup_config is None and app_settings_service is not None:
        try:
            startup_config = load_effective_project_config(app_data_paths)
        except _EXPECTED_STARTUP_SETUP_EXCEPTIONS:
            startup_config = None

    if openai_secret_service is None:
        openai_secret_service = build_openai_secret_service()

    setup_initialisation = initialise_setup_state(
        app_data_paths=app_data_paths,
        config=startup_config,
        openai_secret_service=openai_secret_service,
    )

    app.state.app_data_paths = app_data_paths
    app.state.setup_status = setup_initialisation.status
    app.state.explicit_config = config
    app.state.app_settings_service = app_settings_service
    app.state.openai_secret_service = openai_secret_service
    app.state.setup_status_service = SetupStatusService(
        app_data_paths=app_data_paths,
        openai_secret_service=openai_secret_service,
    )

    if (
        setup_initialisation.config is not None
        and setup_initialisation.profile_paths is not None
    ):
        engine = create_sqlite_engine(setup_initialisation.profile_paths.database_file)
        app.state.config = setup_initialisation.config
        app.state.profile_paths = setup_initialisation.profile_paths
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)

    @app.middleware("http")
    async def setup_redirect_gate(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        setup_status = request.app.state.setup_status_service.build_status(
            config=request.app.state.explicit_config
        )
        request.app.state.setup_status = setup_status
        if setup_status.is_complete and not hasattr(
            request.app.state, "session_factory"
        ):
            refresh_runtime_state(request.app, config=request.app.state.explicit_config)
        if not setup_status.is_complete and _requires_completed_setup(request.url.path):
            return RedirectResponse(
                url="/setup",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        return await call_next(request)

    app.include_router(health_router)
    app.include_router(setup_router)
    app.include_router(settings_router)
    app.include_router(data_folder_router)
    app.include_router(profiles_router)
    app.include_router(applications_router)
    app.include_router(review_router)
    app.include_router(dashboard_router)
    app.include_router(web_router)

    return app


def _requires_completed_setup(path: str) -> bool:
    return not _is_setup_gate_exempt_path(path)


def _is_setup_gate_exempt_path(path: str) -> bool:
    if path in _SETUP_GATE_EXEMPT_PATHS:
        return True

    if path == "/profiles" or path.startswith("/profiles/"):
        return True

    return path.startswith("/docs/")


app = create_app()

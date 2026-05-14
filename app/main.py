from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import RedirectResponse, Response

from app.api.routes_applications import router as applications_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_health import router as health_router
from app.api.routes_review import router as review_router
from app.api.routes_setup import router as setup_router
from app.core.config import ProjectConfig
from app.db.session import create_session_factory, create_sqlite_engine
from app.settings.init import initialise_app_settings_storage
from app.settings.service import load_effective_project_config
from app.setup.init import initialise_setup_state
from app.setup.service import SetupStatusService
from app.storage.bootstrap import bootstrap_app_data_dirs
from app.web.routes import router as web_router

_SETUP_GATE_EXEMPT_PATHS = {
    "/setup",
    "/health/live",
    "/health/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def create_app(config: ProjectConfig | None = None) -> FastAPI:
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
    except Exception:
        app_settings_service = None

    startup_config = config
    if startup_config is None and app_settings_service is not None:
        try:
            startup_config = load_effective_project_config(app_data_paths)
        except Exception:
            startup_config = None

    setup_initialisation = initialise_setup_state(
        app_data_paths=app_data_paths,
        config=startup_config,
    )

    app.state.app_data_paths = app_data_paths
    app.state.setup_status = setup_initialisation.status
    app.state.explicit_config = config
    app.state.app_settings_service = app_settings_service
    app.state.setup_status_service = SetupStatusService(app_data_paths=app_data_paths)

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
            _hydrate_runtime_state(
                request.app, config=request.app.state.explicit_config
            )
        if not setup_status.is_complete and _requires_completed_setup(request.url.path):
            return RedirectResponse(
                url="/setup",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        return await call_next(request)

    app.include_router(health_router)
    app.include_router(setup_router)
    app.include_router(applications_router)
    app.include_router(review_router)
    app.include_router(dashboard_router)
    app.include_router(web_router)

    return app


def _hydrate_runtime_state(app: FastAPI, *, config: ProjectConfig | None) -> None:
    setup_initialisation = initialise_setup_state(
        app_data_paths=app.state.app_data_paths,
        config=config,
    )
    if (
        setup_initialisation.config is None
        or setup_initialisation.profile_paths is None
        or not setup_initialisation.status.is_complete
    ):
        return

    engine = create_sqlite_engine(setup_initialisation.profile_paths.database_file)
    app.state.config = setup_initialisation.config
    app.state.profile_paths = setup_initialisation.profile_paths
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)


def _requires_completed_setup(path: str) -> bool:
    if path in _SETUP_GATE_EXEMPT_PATHS:
        return False

    return not path.startswith("/docs/")


app = create_app()

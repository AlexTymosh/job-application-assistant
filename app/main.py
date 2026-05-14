from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_applications import router as applications_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_health import router as health_router
from app.api.routes_review import router as review_router
from app.core.config import (
    ProjectConfig,
    load_profile_config,
    validate_llm_runtime_config,
)
from app.core.paths import build_profile_paths
from app.db.session import create_session_factory, create_sqlite_engine
from app.web.routes import router as web_router


def create_app(config: ProjectConfig | None = None) -> FastAPI:
    resolved_config = config or load_profile_config()
    validate_llm_runtime_config(resolved_config)

    app = FastAPI(
        title="Local Job Application Assistant",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    profile_paths = build_profile_paths(resolved_config)
    engine = create_sqlite_engine(profile_paths.database_file)

    app.state.config = resolved_config
    app.state.profile_paths = profile_paths
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    app.include_router(health_router)
    app.include_router(applications_router)
    app.include_router(review_router)
    app.include_router(dashboard_router)
    app.include_router(web_router)

    return app


app = create_app()

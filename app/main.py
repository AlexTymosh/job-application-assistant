from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.core.config import ProjectConfig, load_profile_config
from app.core.paths import build_profile_paths
from app.web.routes import router as web_router


def create_app(config: ProjectConfig | None = None) -> FastAPI:
    resolved_config = config or load_profile_config()

    app = FastAPI(
        title="Local Job Application Assistant",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.state.config = resolved_config
    app.state.profile_paths = build_profile_paths(resolved_config)

    app.include_router(health_router)
    app.include_router(web_router)

    return app


app = create_app()

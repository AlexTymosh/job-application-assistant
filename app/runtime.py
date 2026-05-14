from __future__ import annotations

from fastapi import FastAPI

from app.core.config import ProjectConfig
from app.db.session import create_session_factory, create_sqlite_engine
from app.settings.init import initialise_app_settings_storage
from app.setup.init import initialise_setup_state
from app.setup.service import SetupStatusService
from app.storage.app_dirs import AppDataPaths

_RUNTIME_STATE_NAMES = ("config", "profile_paths", "engine", "session_factory")


def refresh_runtime_state(app: FastAPI, *, config: ProjectConfig | None = None) -> bool:
    """Refresh runtime state from the current setup/configuration boundary."""

    setup_initialisation = initialise_setup_state(
        app_data_paths=app.state.app_data_paths,
        config=config,
        openai_secret_service=app.state.openai_secret_service,
    )
    app.state.setup_status = setup_initialisation.status

    if (
        setup_initialisation.config is None
        or setup_initialisation.profile_paths is None
        or not setup_initialisation.status.is_complete
    ):
        _clear_runtime_state(app)
        return False

    old_engine = getattr(app.state, "engine", None)
    engine = create_sqlite_engine(setup_initialisation.profile_paths.database_file)
    app.state.config = setup_initialisation.config
    app.state.profile_paths = setup_initialisation.profile_paths
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    if old_engine is not None and old_engine is not engine:
        old_engine.dispose()
    return True


def _clear_runtime_state(app: FastAPI) -> None:
    old_engine = getattr(app.state, "engine", None)
    for name in _RUNTIME_STATE_NAMES:
        if hasattr(app.state, name):
            delattr(app.state, name)
    if old_engine is not None:
        old_engine.dispose()


def refresh_app_data_state(app: FastAPI, app_data_paths: AppDataPaths) -> bool:
    """Refresh app state after the active app data folder changes."""

    _clear_runtime_state(app)
    app.state.app_data_paths = app_data_paths
    app.state.app_settings_service = initialise_app_settings_storage(app_data_paths)
    app.state.setup_status_service = SetupStatusService(
        app_data_paths=app_data_paths,
        openai_secret_service=app.state.openai_secret_service,
    )
    return refresh_runtime_state(app, config=app.state.explicit_config)

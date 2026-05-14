from __future__ import annotations

from app.settings.migrations import migrate_app_settings_database
from app.settings.service import AppSettingsService, build_app_settings_service
from app.settings.session import create_settings_engine, create_settings_session_factory
from app.storage.app_dirs import AppDataPaths


def initialise_app_settings_storage(app_data_paths: AppDataPaths) -> AppSettingsService:
    migrate_app_settings_database(app_data_paths.database_file)
    engine = create_settings_engine(app_data_paths.database_file)
    session_factory = create_settings_session_factory(engine)
    return build_app_settings_service(session_factory)

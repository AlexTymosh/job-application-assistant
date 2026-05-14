from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.settings.models import AppSetting
from app.settings.schema import (
    StoredAppSetting,
    validate_managed_setting_key,
    validate_stored_setting_value,
)


class AppSettingsRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_setting(self, key: str) -> Any | None:
        key = validate_managed_setting_key(key)
        with self._session_factory() as session:
            row = session.get(AppSetting, key)
            if row is None:
                return None
            raw_value = json.loads(row.value_json)
            return validate_stored_setting_value(key, raw_value)

    def set_setting(self, key: str, value: Any) -> None:
        key = validate_managed_setting_key(key)
        serialised_value = validate_stored_setting_value(key, value)
        value_json = json.dumps(_jsonable_value(serialised_value), sort_keys=True)
        with self._session_factory() as session:
            row = session.get(AppSetting, key)
            if row is None:
                row = AppSetting(key=key, value_json=value_json)
                session.add(row)
            else:
                row.value_json = value_json
            session.commit()

    def delete_setting(self, key: str) -> None:
        key = validate_managed_setting_key(key)
        with self._session_factory() as session:
            row = session.get(AppSetting, key)
            if row is not None:
                session.delete(row)
            session.commit()

    def list_settings(self) -> list[StoredAppSetting]:
        with self._session_factory() as session:
            rows: Iterable[AppSetting] = session.scalars(
                select(AppSetting).order_by(AppSetting.key)
            )
            settings = []
            for row in rows:
                raw_value = json.loads(row.value_json)
                settings.append(
                    StoredAppSetting(
                        key=row.key,
                        value=validate_stored_setting_value(row.key, raw_value),
                    )
                )
            return settings


def _jsonable_value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "as_posix"):
        return value.as_posix()
    return value

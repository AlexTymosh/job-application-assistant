from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated
from urllib.parse import parse_qs

from fastapi import Depends, Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    with factory() as session:
        yield session


def get_app_data_root(request: Request) -> Path:
    return request.app.state.app_data_paths.root


SessionDep = Annotated[Session, Depends(get_session)]
AppDataRootDep = Annotated[Path, Depends(get_app_data_root)]


async def read_form_data(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


async def read_form_multi_data(request: Request) -> dict[str, str | list[str]]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {
        key: values if len(values) > 1 else values[-1] if values else ""
        for key, values in parsed.items()
    }


def form_bool(data: dict[str, str], key: str) -> bool:
    return data.get(key, "").lower() in {"true", "on", "1", "yes"}

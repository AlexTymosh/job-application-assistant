from tests.support.paths import PROJECT_ROOT

ROOT = PROJECT_ROOT


def test_alembic_environment_files_exist() -> None:
    required_files = [
        "alembic.ini",
        "alembic/env.py",
        "alembic/README",
        "alembic/script.py.mako",
        "alembic/versions/20260512_0001_initial_application_tables.py",
    ]

    missing_files = [path for path in required_files if not (ROOT / path).is_file()]

    assert missing_files == []


def test_alembic_versions_directory_is_tracked() -> None:
    assert (ROOT / "alembic" / "versions" / ".gitkeep").is_file()

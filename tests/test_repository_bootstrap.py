import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


REQUIRED_PROJECT_FILES = [
    ".gitignore",
    ".pre-commit-config.yaml",
    ".python-version",
    "AGENTS.md",
    "LICENSE",
    "README.md",
    "SESSION_NOTES.md",
    "Taskfile.yml",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    ".env.example",
    "profiles/example/config.example.yaml",
    "profiles/example/blacklist.example.txt",
    "profiles/example/cv/master.example.md",
    "profiles/example/cv/fact_bank.example.yaml",
    "profiles/example/cv/variants/backend_developer.example.md",
    "app/__init__.py",
    "app/main.py",
    "app/api/__init__.py",
    "app/api/routes_health.py",
    "app/core/__init__.py",
    "app/core/config.py",
    "app/core/paths.py",
    "app/web/__init__.py",
    "app/web/routes.py",
    "app/web/templates/base.html",
    "app/web/templates/index.html",
    "tests/test_config.py",
    "tests/test_health.py",
    "tests/test_paths.py",
    "app/db/__init__.py",
    "app/db/base.py",
    "app/db/models.py",
    "app/db/repositories.py",
    "app/db/session.py",
    "tests/test_db_models.py",
    "tests/test_repositories.py",
    "alembic.ini",
    "alembic/env.py",
    "alembic/README",
    "alembic/script.py.mako",
    "alembic/versions/.gitkeep",
    "alembic/versions/20260512_0001_initial_application_tables.py",
    "tests/test_alembic_setup.py",
]


PRIVATE_PATHS_THAT_MUST_NOT_BE_TRACKED = [
    ".env",
    "profiles/alex/config.yaml",
    "profiles/alex/blacklist.txt",
    "profiles/alex/applications.sqlite3",
    "profiles/alex/cv/master.md",
    "profiles/alex/cv/fact_bank.yaml",
    "profiles/alex/cv/variants/backend_developer.md",
    "profiles/alex/resume/master.md",
    "profiles/alex/resume/fact_bank.yaml",
    "profiles/alex/resume/variants/backend_developer.md",
]


def test_required_bootstrap_files_exist() -> None:
    missing_files = [
        relative_path
        for relative_path in REQUIRED_PROJECT_FILES
        if not (ROOT / relative_path).is_file()
    ]

    assert missing_files == []


def test_private_profile_files_are_not_tracked_by_git() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--", *PRIVATE_PATHS_THAT_MUST_NOT_BE_TRACKED],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    tracked_private_files = [
        line.strip() for line in result.stdout.splitlines() if line.strip()
    ]

    assert tracked_private_files == []


def test_example_profile_uses_example_suffixes() -> None:
    example_profile_files = [
        path for path in (ROOT / "profiles" / "example").rglob("*") if path.is_file()
    ]

    unsafe_files = [
        path.relative_to(ROOT).as_posix()
        for path in example_profile_files
        if path.name in {"config.yaml", "blacklist.txt", "master.md", "fact_bank.yaml"}
    ]

    assert unsafe_files == []


def test_required_bootstrap_files_are_tracked_by_git() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--", *REQUIRED_PROJECT_FILES],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    tracked_files = {
        line.strip() for line in result.stdout.splitlines() if line.strip()
    }

    missing_from_git = [
        relative_path
        for relative_path in REQUIRED_PROJECT_FILES
        if relative_path not in tracked_files
    ]

    assert missing_from_git == []


def test_documentation_does_not_use_uppercase_cv_paths() -> None:
    docs_to_check = [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "SESSION_NOTES.md",
    ]

    forbidden_fragments = [
        "app/CV/",
        "profiles/alex/CV/",
        "profiles/example/CV/",
    ]

    violations = []

    for document_path in docs_to_check:
        content = document_path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in content:
                violations.append(
                    f"{document_path.relative_to(ROOT)} contains {fragment}"
                )

    assert violations == []

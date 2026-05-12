from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


REQUIRED_BOOTSTRAP_FILES = [
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
        for relative_path in REQUIRED_BOOTSTRAP_FILES
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
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    assert tracked_private_files == []


def test_example_profile_uses_example_suffixes() -> None:
    example_profile_files = [
        path
        for path in (ROOT / "profiles" / "example").rglob("*")
        if path.is_file()
    ]

    unsafe_files = [
        path.relative_to(ROOT).as_posix()
        for path in example_profile_files
        if path.name in {"config.yaml", "blacklist.txt", "master.md", "fact_bank.yaml"}
    ]

    assert unsafe_files == []
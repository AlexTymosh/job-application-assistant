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
    "docs/release-checklist.md",
    "docs/manual-smoke-test.md",
    "docs/local-profile-setup.md",
    "Taskfile.yml",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    ".env.example",
    "profiles/example/config.example.yaml",
    "profiles/example/blacklist.example.txt",
    "profiles/example/cv/fact_bank.example.yaml",
    "profiles/example/cv/variants/backend_developer.example.md",
    "app/__init__.py",
    "app/main.py",
    "app/runtime.py",
    "app/api/__init__.py",
    "app/api/routes_health.py",
    "app/api/routes_setup.py",
    "app/api/routes_settings.py",
    "app/api/routes_data_folder.py",
    "app/api/routes_profiles.py",
    "app/api/dependencies.py",
    "app/api/routes_applications.py",
    "app/api/routes_review.py",
    "app/api/routes_dashboard.py",
    "app/core/__init__.py",
    "app/core/config.py",
    "app/core/paths.py",
    "app/storage/__init__.py",
    "app/storage/app_dirs.py",
    "app/storage/bootstrap.py",
    "app/storage/location.py",
    "app/storage/service.py",
    "app/setup/__init__.py",
    "app/setup/init.py",
    "app/setup/checks.py",
    "app/setup/service.py",
    "app/settings/__init__.py",
    "app/settings/base.py",
    "app/settings/init.py",
    "app/settings/form_models.py",
    "app/settings/migrations.py",
    "app/settings/models.py",
    "app/settings/repository.py",
    "app/settings/schema.py",
    "app/settings/service.py",
    "app/settings/session.py",
    "app/settings/secret_form.py",
    "app/profiles/__init__.py",
    "app/profiles/form_models.py",
    "app/profiles/models.py",
    "app/profiles/repository.py",
    "app/profiles/schema.py",
    "app/profiles/service.py",
    "app/profiles/validation.py",
    "app/secrets/__init__.py",
    "app/secrets/openai_key.py",
    "tests/test_openai_secret_service.py",
    "tests/test_llm_factory.py",
    "tests/test_app_settings_storage.py",
    "tests/test_app_settings_config_overlay.py",
    "app/web/__init__.py",
    "app/web/routes.py",
    "app/web/templating.py",
    "app/web/templates/applications_new.html",
    "app/web/templates/applications_detail.html",
    "app/web/templates/review.html",
    "app/web/templates/dashboard.html",
    "app/web/templates/error.html",
    "app/web/templates/base.html",
    "app/web/templates/index.html",
    "app/web/templates/setup.html",
    "app/web/templates/settings.html",
    "app/web/templates/data_folder.html",
    "app/web/templates/profiles.html",
    "tests/test_config.py",
    "tests/test_health.py",
    "tests/test_application_routes.py",
    "tests/test_review_routes.py",
    "tests/test_dashboard_routes.py",
    "tests/test_paths.py",
    "tests/test_app_dirs.py",
    "tests/test_storage_bootstrap.py",
    "tests/test_setup_checks.py",
    "tests/test_setup_routes.py",
    "tests/test_settings_routes.py",
    "tests/test_data_folder.py",
    "tests/test_managed_profiles_storage.py",
    "tests/test_profiles_routes.py",
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
    "alembic/versions/20260514_0002_add_application_artifact_dir_name.py",
    "alembic/versions/20260514_0003_add_application_numbers.py",
    "tests/test_alembic_setup.py",
    "app/jobs/__init__.py",
    "app/jobs/hashing.py",
    "app/jobs/input_models.py",
    "app/jobs/normalisation.py",
    "app/jobs/service.py",
    "tests/test_job_hashing.py",
    "tests/test_job_input_models.py",
    "tests/test_job_normalisation.py",
    "tests/test_job_service.py",
    "app/preflight/__init__.py",
    "app/preflight/blacklist.py",
    "app/preflight/duplicate_detection.py",
    "app/preflight/prompt_injection.py",
    "app/preflight/service.py",
    "tests/test_blacklist.py",
    "tests/test_duplicate_detection.py",
    "tests/test_prompt_injection.py",
    "tests/test_preflight_service.py",
    "app/preflight/persistence.py",
    "tests/test_preflight_persistence.py",
    "app/pipeline/__init__.py",
    "app/pipeline/intake.py",
    "app/pipeline/state.py",
    "app/pipeline/job_extraction.py",
    "app/pipeline/extraction_persistence.py",
    "tests/test_application_intake.py",
    "app/llm/__init__.py",
    "app/llm/errors.py",
    "app/llm/schemas.py",
    "app/llm/fake_client.py",
    "app/llm/openai_client.py",
    "app/llm/factory.py",
    "app/llm/tailoring_schemas.py",
    "app/llm/fake_tailor.py",
    "app/llm/prompts/job_extraction.md",
    "tests/test_llm_schemas.py",
    "tests/test_fake_llm_client.py",
    "tests/test_pipeline_state.py",
    "tests/test_job_extraction_step.py",
    "tests/test_openai_client_contract.py",
    "tests/test_extraction_persistence.py",
    "tests/test_tailoring_schemas.py",
    "tests/test_fake_tailor.py",
    "tests/test_cv_diff.py",
    "tests/test_cv_tailoring_step.py",
    "app/pipeline/cv_tailoring.py",
    "app/artifacts/__init__.py",
    "app/artifacts/naming.py",
    "app/artifacts/paths.py",
    "app/artifacts/writer.py",
    "app/artifacts/resolution.py",
    "app/cv/__init__.py",
    "app/cv/models.py",
    "app/cv/markdown_loader.py",
    "app/cv/section_parser.py",
    "app/cv/fact_bank.py",
    "app/cv/selector.py",
    "app/cv/diff.py",
    "app/reports/__init__.py",
    "app/reports/models.py",
    "app/reports/evidence_matrix.py",
    "app/reports/match_report.py",
    "app/exporters/markdown_exporter.py",
    "app/exporters/html_exporter.py",
    "app/exporters/pdf_exporter.py",
    "app/exporters/docx_exporter.py",
    "app/pipeline/export_markdown_html.py",
    "app/pipeline/export_pdf_docx.py",
    "app/pipeline/local_web_pipeline.py",
    "tests/test_artifact_download_routes.py",
    "tests/test_local_pipeline_routes.py",
    "tests/test_markdown_exporter.py",
    "tests/test_html_exporter.py",
    "tests/test_export_markdown_html.py",
    "tests/test_pdf_exporter.py",
    "tests/test_docx_exporter.py",
    "tests/test_export_pdf_docx.py",
    "tests/test_cv_markdown_loader.py",
    "tests/test_cv_section_parser.py",
    "tests/test_fact_bank.py",
    "tests/test_cv_selector.py",
    "tests/test_artifact_naming.py",
    "tests/test_artifact_paths.py",
    "tests/test_artifact_writer.py",
    "tests/test_report_models.py",
    "tests/test_evidence_matrix.py",
    "tests/test_match_report.py",
    "tests/test_alembic_migrations.py",
]


PRIVATE_PATHS_THAT_MUST_NOT_BE_TRACKED = [
    ".env",
    "profiles/alex/config.yaml",
    "profiles/alex/blacklist.txt",
    "profiles/alex/applications.sqlite3",
    "profiles/alex/cv/fact_bank.yaml",
    "profiles/alex/cv/variants/backend_developer.md",
    "profiles/alex/resume/fact_bank.yaml",
    "profiles/alex/resume/variants/backend_developer.md",
    "profiles/example/applications.sqlite3",
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
        if path.name in {"config.yaml", "blacklist.txt", "fact_bank.yaml"}
    ]

    assert unsafe_files == []


def test_example_profile_has_at_least_one_example_cv_variant() -> None:
    expected_variant = (
        ROOT
        / "profiles"
        / "example"
        / "cv"
        / "variants"
        / "backend_developer.example.md"
    )

    assert expected_variant.is_file()


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


def test_release_documentation_is_safe_and_actionable() -> None:
    release_doc_paths = [
        ROOT / "docs" / "release-checklist.md",
        ROOT / "docs" / "manual-smoke-test.md",
        ROOT / "docs" / "local-profile-setup.md",
    ]

    combined_content = "\n".join(
        path.read_text(encoding="utf-8") for path in release_doc_paths
    )
    lower_content = combined_content.lower()

    forbidden_fragments = [
        "sk-",
        "@gmail.com",
        "@outlook.com",
        "@hotmail.com",
        "c:/users/alex/",
        "c:\\users\\alex\\",
    ]

    violations = [
        fragment for fragment in forbidden_fragments if fragment in lower_content
    ]

    assert violations == []
    assert "external" in lower_content
    assert "outside the repository" in lower_content
    assert "uv sync --locked --group dev" in combined_content
    assert "tests must not call the real openai api" in lower_content


def test_generated_sqlite_files_are_ignored_by_git() -> None:
    ignored_paths = [
        "profiles/example/applications.sqlite3",
        "profiles/alex/applications.sqlite3",
    ]

    result = subprocess.run(
        ["git", "check-ignore", "-v", *ignored_paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    ignored = {line.rsplit("\t", maxsplit=1)[-1] for line in result.stdout.splitlines()}

    assert ignored == set(ignored_paths)

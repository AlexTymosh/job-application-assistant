from __future__ import annotations

from pathlib import Path

from app.db.session import create_all_tables, create_sqlite_engine


def write_file_based_profile(
    path: Path,
    *,
    name: str = "alex",
    with_database: bool = True,
    fact_bank_content: str | None = None,
    cv_content: str | None = None,
) -> None:
    (path / "cv" / "variants").mkdir(parents=True)

    (path / "config.yaml").write_text(
        f"""
app:
  profile_name: {name}
  data_dir: {path.as_posix()}
workflow:
  require_human_approval_before_export: true
llm:
  extraction_mode: fake
cv:
  default_variant: backend_developer
  variants:
    - backend_developer
exports: {{}}
guardrails: {{}}
job_reader: {{}}
future_integrations: {{}}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (path / "cv" / "fact_bank.yaml").write_text(
        fact_bank_content
        or """
facts:
  - id: fact-1
    category: skill
    name: Backend services
    allowed_claim_level: practical
    evidence: Built Python and FastAPI services in verified work.
""".lstrip(),
        encoding="utf-8",
    )

    (path / "cv" / "variants" / "backend_developer.md").write_text(
        cv_content or valid_cv_content(),
        encoding="utf-8",
    )

    if with_database:
        engine = create_sqlite_engine(path / "applications.sqlite3")
        create_all_tables(engine)
        engine.dispose()


def valid_cv_content(marker: str = "Backend Developer CV") -> str:
    return (
        f"# {marker}\n\n"
        "<!-- SECTION: SUMMARY_START -->\n"
        "Backend-focused software developer.\n"
        "<!-- SECTION: SUMMARY_END -->\n\n"
        "<!-- SECTION: SKILLS_START -->\n"
        "- Python\n"
        "- FastAPI\n"
        "<!-- SECTION: SKILLS_END -->\n\n"
        "<!-- SECTION: EXPERIENCE_START -->\n"
        "## Example Company\n\n"
        "- Built internal tooling.\n"
        "<!-- SECTION: EXPERIENCE_END -->\n\n"
        "<!-- SECTION: PROJECTS_START -->\n"
        "## Local FastAPI Project\n\n"
        "- Built a FastAPI project.\n"
        "<!-- SECTION: PROJECTS_END -->\n"
    )

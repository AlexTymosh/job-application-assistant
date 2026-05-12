from app.jobs.hashing import build_job_text_hash, normalise_text_for_hashing


def test_normalise_text_for_hashing_collapses_whitespace() -> None:
    assert normalise_text_for_hashing("  hello   world\nagain ") == "hello world again"


def test_build_job_text_hash_is_stable_for_whitespace_changes() -> None:
    first_hash = build_job_text_hash("Senior Python Developer\n\nFastAPI")
    second_hash = build_job_text_hash(" Senior   Python Developer FastAPI ")

    assert first_hash == second_hash


def test_build_job_text_hash_changes_for_different_text() -> None:
    first_hash = build_job_text_hash("Senior Python Developer")
    second_hash = build_job_text_hash("Junior Python Developer")

    assert first_hash != second_hash


def test_build_job_text_hash_returns_sha256_hex_digest() -> None:
    job_hash = build_job_text_hash("Senior Python Developer")

    assert len(job_hash) == 64

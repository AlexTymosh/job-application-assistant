from pathlib import Path

from app.preflight.blacklist import find_blacklist_matches, load_blacklist_entries


def test_load_blacklist_entries_ignores_empty_lines_and_comments(
    tmp_path: Path,
) -> None:
    blacklist_path = tmp_path / "blacklist.txt"
    blacklist_path.write_text(
        "\n# comment\nBad Company\nspam recruiter\n   \n",
        encoding="utf-8",
    )

    result = load_blacklist_entries(blacklist_path)

    assert result == ["bad company", "spam recruiter"]


def test_load_blacklist_entries_returns_empty_list_for_missing_file(
    tmp_path: Path,
) -> None:
    result = load_blacklist_entries(tmp_path / "missing_blacklist.txt")

    assert result == []


def test_find_blacklist_matches_finds_case_insensitive_matches() -> None:
    result = find_blacklist_matches(
        text="This role is from Bad Company and a spam recruiter.",
        entries=["bad company", "spam recruiter", "another company"],
    )

    assert result == ["bad company", "spam recruiter"]


def test_find_blacklist_matches_returns_empty_list_when_no_matches() -> None:
    result = find_blacklist_matches(
        text="This is a normal Python backend developer role.",
        entries=["bad company", "spam recruiter"],
    )

    assert result == []

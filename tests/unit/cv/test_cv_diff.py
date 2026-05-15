from app.cv.diff import build_unified_diff, has_meaningful_diff


def test_has_meaningful_diff_returns_false_for_equal_text() -> None:
    assert (
        has_meaningful_diff("Line one\r\nLine two\n", "Line one\nLine two\n") is False
    )


def test_has_meaningful_diff_returns_true_for_changed_text() -> None:
    assert has_meaningful_diff("Line one\n", "Line two\n") is True


def test_build_unified_diff_includes_before_and_after_filenames() -> None:
    diff = build_unified_diff("Old\n", "New\n", fromfile="old.md", tofile="new.md")

    assert "--- old.md" in diff
    assert "+++ new.md" in diff


def test_build_unified_diff_includes_removed_and_added_lines() -> None:
    diff = build_unified_diff("Old\n", "New\n")

    assert "-Old" in diff
    assert "+New" in diff

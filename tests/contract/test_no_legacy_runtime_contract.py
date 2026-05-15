from __future__ import annotations

from pathlib import Path


def test_legacy_profile_examples_removed():
    assert not Path("profiles/example/config.example.yaml").exists()
    assert not Path("profiles/example/cv/fact_bank.example.yaml").exists()


def test_documentation_does_not_instruct_yaml_source_of_truth():
    docs = [Path("README.md"), *Path("docs").glob("*.md")]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in docs if path.exists()).lower()
    assert "fact_bank.yaml" not in combined
    assert "config.yaml" not in combined
    assert "markdown cv" not in combined

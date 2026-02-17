"""Tests for detect_instruction_files() and detect_design_docs()."""

from agentic_dev_pipeline.detect import detect_design_docs, detect_instruction_files


class TestDetectInstructionFiles:
    def test_claude_md(self, tmp_path, clean_env):
        (tmp_path / "CLAUDE.md").write_text("# Rules\n")
        result = detect_instruction_files(tmp_path)
        assert "CLAUDE.md" in result

    def test_multiple_files(self, tmp_path, clean_env):
        (tmp_path / "CLAUDE.md").write_text("# Rules\n")
        (tmp_path / "CONTRIBUTING.md").write_text("# Contributing\n")
        result = detect_instruction_files(tmp_path)
        assert "CLAUDE.md" in result
        assert "CONTRIBUTING.md" in result

    def test_claude_rules_dir(self, tmp_path, clean_env):
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "coding.md").write_text("# Coding rules\n")
        (rules_dir / "testing.md").write_text("# Testing rules\n")
        result = detect_instruction_files(tmp_path)
        assert any("coding.md" in f for f in result)
        assert any("testing.md" in f for f in result)

    def test_no_files(self, tmp_path, clean_env):
        assert detect_instruction_files(tmp_path) == []

    def test_env_override(self, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("INSTRUCTION_FILES", "custom.md rules.md")
        result = detect_instruction_files(tmp_path)
        assert result == ["custom.md", "rules.md"]

    def test_no_duplicates(self, tmp_path, clean_env):
        (tmp_path / "CLAUDE.md").write_text("# Rules\n")
        result = detect_instruction_files(tmp_path)
        assert len(result) == len(set(result))


class TestDetectDesignDocs:
    def test_architecture_md(self, tmp_path, clean_env):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "architecture.md").write_text("# Arch\n")
        result = detect_design_docs(tmp_path)
        assert "docs/architecture.md" in result

    def test_architecture_md_root(self, tmp_path, clean_env):
        (tmp_path / "ARCHITECTURE.md").write_text("# Arch\n")
        result = detect_design_docs(tmp_path)
        assert "ARCHITECTURE.md" in result

    def test_no_docs(self, tmp_path, clean_env):
        assert detect_design_docs(tmp_path) == []

    def test_env_override(self, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("DESIGN_DOCS", "design.md")
        result = detect_design_docs(tmp_path)
        assert result == ["design.md"]

"""Tests for init scaffolding command."""


from agentic_dev_pipeline.init_cmd import run_init


class TestRunInit:
    def test_creates_files_in_empty_dir(self, tmp_path):
        actions = run_init(tmp_path)
        assert (tmp_path / "PROMPT.md").is_file()
        assert (tmp_path / "requirements.md").is_file()
        assert (tmp_path / ".gitignore").is_file()
        # No pyproject.toml → standalone .toml
        assert (tmp_path / ".agentic-dev-pipeline.toml").is_file()
        assert any("Created" in a for a in actions)

    def test_skips_existing_files(self, tmp_path):
        (tmp_path / "PROMPT.md").write_text("custom prompt")
        (tmp_path / "requirements.md").write_text("custom req")
        actions = run_init(tmp_path)
        # Should not overwrite
        assert (tmp_path / "PROMPT.md").read_text() == "custom prompt"
        assert (tmp_path / "requirements.md").read_text() == "custom req"
        assert any("Skipped" in a for a in actions)

    def test_force_overwrites(self, tmp_path):
        (tmp_path / "PROMPT.md").write_text("old")
        run_init(tmp_path, force=True)
        content = (tmp_path / "PROMPT.md").read_text()
        assert content != "old"
        assert "Feature" in content

    def test_pyproject_gets_section(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
        run_init(tmp_path)
        content = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.agentic-dev-pipeline]" in content
        assert 'prompt-file = "PROMPT.md"' in content
        # Should NOT create standalone toml when pyproject exists
        assert not (tmp_path / ".agentic-dev-pipeline.toml").is_file()

    def test_pyproject_skips_existing_section(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\n\n[tool.agentic-dev-pipeline]\nprompt-file = "P.md"\n'
        )
        actions = run_init(tmp_path)
        assert any("Skipped pyproject.toml" in a for a in actions)

    def test_standalone_toml_created(self, tmp_path):
        # No pyproject.toml
        run_init(tmp_path)
        toml = tmp_path / ".agentic-dev-pipeline.toml"
        assert toml.is_file()
        content = toml.read_text()
        assert 'prompt-file = "PROMPT.md"' in content

    def test_gitignore_appended(self, tmp_path):
        (tmp_path / ".gitignore").write_text("node_modules/\n")
        run_init(tmp_path)
        content = (tmp_path / ".gitignore").read_text()
        assert ".agentic-dev-pipeline/" in content
        assert "node_modules/" in content

    def test_gitignore_not_duplicated(self, tmp_path):
        (tmp_path / ".gitignore").write_text("node_modules/\n.agentic-dev-pipeline/\n")
        actions = run_init(tmp_path)
        content = (tmp_path / ".gitignore").read_text()
        assert content.count(".agentic-dev-pipeline/") == 1
        assert any("Skipped .gitignore" in a for a in actions)

    def test_gitignore_created_if_missing(self, tmp_path):
        run_init(tmp_path)
        assert (tmp_path / ".gitignore").is_file()
        assert ".agentic-dev-pipeline/" in (tmp_path / ".gitignore").read_text()

    def test_gitignore_newline_before_entry(self, tmp_path):
        # File without trailing newline
        (tmp_path / ".gitignore").write_text("node_modules/")
        run_init(tmp_path)
        content = (tmp_path / ".gitignore").read_text()
        assert content == "node_modules/\n.agentic-dev-pipeline/\n"

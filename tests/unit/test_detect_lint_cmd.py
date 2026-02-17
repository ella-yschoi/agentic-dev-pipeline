"""Tests for detect_lint_cmd()."""

import sys

from agentic_dev_pipeline.detect import detect_lint_cmd


class TestDetectLintCmd:
    def test_env_override(self, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("LINT_CMD", "custom-lint .")
        assert detect_lint_cmd(project_root=tmp_path) == "custom-lint ."

    def test_makefile_target(self, tmp_path, clean_env):
        (tmp_path / "Makefile").write_text("lint:\n\techo lint\n")
        assert detect_lint_cmd(project_root=tmp_path) == "make lint"

    def test_node_npm_script(self, tmp_path, clean_env):
        (tmp_path / "package.json").write_text(
            '{"scripts": {"lint": "eslint ."}}\n'
        )
        result = detect_lint_cmd("node", project_root=tmp_path)
        assert result == "npm run lint"

    def test_rust_clippy(self, tmp_path, clean_env):
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        result = detect_lint_cmd("rust", project_root=tmp_path)
        assert result == "cargo clippy -- -D warnings"

    def test_go_vet_fallback(self, tmp_path, monkeypatch, clean_env, no_venv):
        """Without golangci-lint, falls back to go vet."""
        (tmp_path / "go.mod").write_text("module test\n")
        # Ensure golangci-lint is not found
        monkeypatch.setenv("PATH", "")
        result = detect_lint_cmd("go", project_root=tmp_path)
        assert result == "go vet ./..."

    def test_unknown_project_empty(self, tmp_path, clean_env):
        result = detect_lint_cmd("unknown", project_root=tmp_path)
        assert result == ""

    def test_makefile_priority_over_tool(self, tmp_path, clean_env):
        """Makefile target takes priority over tool existence."""
        (tmp_path / "Makefile").write_text("lint:\n\tmy-custom-lint\n")
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        result = detect_lint_cmd("rust", project_root=tmp_path)
        assert result == "make lint"

    def test_ruff_in_venv_no_runner(self, tmp_path, monkeypatch, clean_env):
        """ruff found in venv uses full path when no runner."""
        monkeypatch.setenv("PATH", "")
        fake_venv = tmp_path / "fake-venv"
        bin_dir = fake_venv / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "ruff").write_text("")
        (bin_dir / "ruff").chmod(0o755)
        monkeypatch.setattr(sys, "prefix", str(fake_venv))
        monkeypatch.setattr(sys, "base_prefix", "/usr")

        (tmp_path / "src").mkdir()
        result = detect_lint_cmd("python", project_root=tmp_path)
        assert result == f"{bin_dir / 'ruff'} check src/"

    def test_ruff_in_venv_with_runner(self, tmp_path, monkeypatch, clean_env):
        """ruff with uv runner uses 'uv run ruff' (not venv path)."""
        fake_venv = tmp_path / "fake-venv"
        bin_dir = fake_venv / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "ruff").write_text("")
        (bin_dir / "ruff").chmod(0o755)
        monkeypatch.setattr(sys, "prefix", str(fake_venv))
        monkeypatch.setattr(sys, "base_prefix", "/usr")

        (tmp_path / "uv.lock").write_text("")
        (tmp_path / "src").mkdir(exist_ok=True)
        result = detect_lint_cmd("python", project_root=tmp_path)
        assert "uv run ruff check" in result

"""Tests for detect_test_cmd()."""

import sys

from agentic_dev_pipeline.detect import detect_test_cmd


class TestDetectTestCmd:
    def test_env_override(self, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("TEST_CMD", "custom-test")
        assert detect_test_cmd(project_root=tmp_path) == "custom-test"

    def test_makefile_target(self, tmp_path, clean_env):
        (tmp_path / "Makefile").write_text("test:\n\techo test\n")
        assert detect_test_cmd(project_root=tmp_path) == "make test"

    def test_node_npm_script(self, tmp_path, clean_env):
        (tmp_path / "package.json").write_text(
            '{"scripts": {"test": "jest"}}\n'
        )
        result = detect_test_cmd("node", project_root=tmp_path)
        assert result == "npm test"

    def test_rust(self, tmp_path, clean_env):
        result = detect_test_cmd("rust", project_root=tmp_path)
        assert result == "cargo test"

    def test_go(self, tmp_path, clean_env):
        result = detect_test_cmd("go", project_root=tmp_path)
        assert result == "go test ./..."

    def test_unknown_project_empty(self, tmp_path, clean_env):
        result = detect_test_cmd("unknown", project_root=tmp_path)
        assert result == ""

    def test_python_unittest_fallback(self, tmp_path, monkeypatch, clean_env, no_venv):
        """Falls back to unittest if pytest not available and tests dir exists."""
        (tmp_path / "tests").mkdir()
        monkeypatch.setenv("PATH", "")  # Remove pytest from PATH
        result = detect_test_cmd("python", project_root=tmp_path)
        assert "unittest" in result

    def test_pytest_in_venv_no_runner(self, tmp_path, monkeypatch, clean_env):
        """pytest found in venv uses full path when no runner."""
        monkeypatch.setenv("PATH", "")
        fake_venv = tmp_path / "fake-venv"
        bin_dir = fake_venv / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "pytest").write_text("")
        (bin_dir / "pytest").chmod(0o755)
        monkeypatch.setattr(sys, "prefix", str(fake_venv))
        monkeypatch.setattr(sys, "base_prefix", "/usr")

        result = detect_test_cmd("python", project_root=tmp_path)
        assert result == f"{bin_dir / 'pytest'} -q"

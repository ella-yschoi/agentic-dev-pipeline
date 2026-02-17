"""Tests for detect_project_type()."""

from agentic_dev_pipeline.detect import detect_project_type


class TestDetectProjectType:
    def test_python_pyproject(self, tmp_path, clean_env):
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        assert detect_project_type(tmp_path) == "python"

    def test_python_setup_py(self, tmp_path, clean_env):
        (tmp_path / "setup.py").write_text("from setuptools import setup\n")
        assert detect_project_type(tmp_path) == "python"

    def test_python_setup_cfg(self, tmp_path, clean_env):
        (tmp_path / "setup.cfg").write_text("[metadata]\n")
        assert detect_project_type(tmp_path) == "python"

    def test_node(self, tmp_path, clean_env):
        (tmp_path / "package.json").write_text("{}\n")
        assert detect_project_type(tmp_path) == "node"

    def test_rust(self, tmp_path, clean_env):
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        assert detect_project_type(tmp_path) == "rust"

    def test_go(self, tmp_path, clean_env):
        (tmp_path / "go.mod").write_text("module test\n")
        assert detect_project_type(tmp_path) == "go"

    def test_unknown(self, tmp_path, clean_env):
        assert detect_project_type(tmp_path) == "unknown"

    def test_env_override(self, tmp_path, monkeypatch, clean_env):
        """PROJECT_TYPE env var overrides file detection."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        monkeypatch.setenv("PROJECT_TYPE", "custom")
        assert detect_project_type(tmp_path) == "custom"

    def test_python_takes_priority_over_node(self, tmp_path, clean_env):
        """If both pyproject.toml and package.json exist, Python wins."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        (tmp_path / "package.json").write_text("{}\n")
        assert detect_project_type(tmp_path) == "python"

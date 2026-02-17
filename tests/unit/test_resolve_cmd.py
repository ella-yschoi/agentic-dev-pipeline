"""Tests for _resolve_cmd() and _cmd_exists() venv fallback."""

import sys

from agentic_dev_pipeline.detect import _cmd_exists, _resolve_cmd


class TestResolveCmd:
    def test_found_on_path(self):
        """Commands on PATH return bare name."""
        assert _resolve_cmd("python") == "python"

    def test_found_in_venv(self, tmp_path, monkeypatch):
        """Commands in venv bin/ return full path when not on PATH."""
        monkeypatch.setenv("PATH", "")
        fake_venv = tmp_path / "fake-venv"
        bin_dir = fake_venv / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "ruff").write_text("")
        (bin_dir / "ruff").chmod(0o755)

        monkeypatch.setattr(sys, "prefix", str(fake_venv))
        monkeypatch.setattr(sys, "base_prefix", "/usr")

        result = _resolve_cmd("ruff")
        assert result == str(bin_dir / "ruff")

    def test_not_found_returns_none(self, tmp_path, monkeypatch, no_venv):
        """Missing commands return None."""
        monkeypatch.setenv("PATH", "")
        assert _resolve_cmd("nonexistent-tool-xyz") is None

    def test_no_venv_fallback_when_not_in_venv(self, tmp_path, monkeypatch, no_venv):
        """No venv fallback when sys.prefix == sys.base_prefix."""
        monkeypatch.setenv("PATH", "")
        assert _resolve_cmd("ruff") is None


class TestCmdExistsVenv:
    def test_delegates_to_resolve_cmd(self, tmp_path, monkeypatch):
        """_cmd_exists returns True when tool is in venv."""
        monkeypatch.setenv("PATH", "")
        fake_venv = tmp_path / "fake-venv"
        bin_dir = fake_venv / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "pytest").write_text("")
        (bin_dir / "pytest").chmod(0o755)

        monkeypatch.setattr(sys, "prefix", str(fake_venv))
        monkeypatch.setattr(sys, "base_prefix", "/usr")

        assert _cmd_exists("pytest") is True

    def test_returns_false_when_missing(self, tmp_path, monkeypatch, no_venv):
        monkeypatch.setenv("PATH", "")
        assert _cmd_exists("nonexistent-tool-xyz") is False

"""Tests for detect_security_cmd()."""

import sys

from agentic_dev_pipeline.detect import detect_security_cmd


class TestDetectSecurityCmd:
    def test_env_override(self, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("SECURITY_CMD", "my-scanner")
        assert detect_security_cmd(project_root=tmp_path) == "my-scanner"

    def test_env_override_empty_skips(self, tmp_path, monkeypatch, clean_env):
        """Setting SECURITY_CMD to empty string should skip security scan."""
        monkeypatch.setenv("SECURITY_CMD", "")
        assert detect_security_cmd(project_root=tmp_path) == ""

    def test_node_npm_audit(self, tmp_path, monkeypatch, clean_env, no_venv):
        """Node projects default to npm audit."""
        monkeypatch.setenv("PATH", "")  # No semgrep
        result = detect_security_cmd("node", project_root=tmp_path)
        assert result == "npm audit --audit-level=high"

    def test_unknown_project_empty(self, tmp_path, monkeypatch, clean_env, no_venv):
        monkeypatch.setenv("PATH", "")
        result = detect_security_cmd("unknown", project_root=tmp_path)
        assert result == ""

    def test_bandit_in_venv_no_runner(self, tmp_path, monkeypatch, clean_env):
        """bandit found in venv uses full path when no runner."""
        monkeypatch.setenv("PATH", "")
        fake_venv = tmp_path / "fake-venv"
        bin_dir = fake_venv / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "bandit").write_text("")
        (bin_dir / "bandit").chmod(0o755)
        monkeypatch.setattr(sys, "prefix", str(fake_venv))
        monkeypatch.setattr(sys, "base_prefix", "/usr")

        (tmp_path / "src").mkdir()
        result = detect_security_cmd("python", project_root=tmp_path)
        assert result == f"{bin_dir / 'bandit'} -r src/ -q"

"""Tests for pipeline module."""

import stat

from agentic_dev_pipeline.pipeline import (
    _is_safe_command,
    _load_plugins,
    _run_callable_gate,
    _run_gate_command,
)


class TestSafeCommand:
    def test_simple_command(self):
        assert _is_safe_command("ruff check src/") is True

    def test_make_command(self):
        assert _is_safe_command("make lint") is True

    def test_npm_command(self):
        assert _is_safe_command("npm test") is True

    def test_command_substitution_dollar(self):
        assert _is_safe_command("echo $(rm -rf /)") is False

    def test_command_substitution_backtick(self):
        assert _is_safe_command("echo `rm -rf /`") is False

    def test_redirect_to_dev(self):
        assert _is_safe_command("cat > /dev/sda") is False

    def test_semicolon_rm(self):
        assert _is_safe_command("echo hi; rm -rf /") is False

    def test_and_rm(self):
        assert _is_safe_command("echo hi && rm -rf /") is False


class TestRunGateCommand:
    def test_successful_command(self):
        passed, output = _run_gate_command("echo hello")
        assert passed is True
        assert "hello" in output

    def test_failing_command(self):
        passed, _output = _run_gate_command("false")
        assert passed is False

    def test_unsafe_command_blocked(self):
        passed, output = _run_gate_command("echo $(cat /etc/passwd)")
        assert passed is False
        assert "BLOCKED" in output

    def test_timeout(self):
        passed, output = _run_gate_command("sleep 10", timeout=1)
        assert passed is False
        assert "timed out" in output


class TestLoadPlugins:
    def test_empty_dir(self, tmp_path):
        assert _load_plugins(str(tmp_path)) == []

    def test_no_dir(self):
        assert _load_plugins("") == []
        assert _load_plugins(None) == []

    def test_sh_plugins(self, tmp_path):
        (tmp_path / "lint-extra.sh").write_text("#!/bin/bash\necho ok\n")
        (tmp_path / "lint-extra.sh").chmod(
            (tmp_path / "lint-extra.sh").stat().st_mode | stat.S_IEXEC
        )
        result = _load_plugins(str(tmp_path))
        assert len(result) == 1
        assert result[0][0] == "lint-extra"
        assert "bash" in result[0][1]

    def test_py_plugins(self, tmp_path):
        (tmp_path / "check.py").write_text("print('ok')\n")
        result = _load_plugins(str(tmp_path))
        assert len(result) == 1
        assert result[0][0] == "check"
        assert "python3" in result[0][1]

    def test_ignores_non_plugin_files(self, tmp_path):
        (tmp_path / "README.md").write_text("# Plugin docs\n")
        (tmp_path / "data.json").write_text("{}\n")
        assert _load_plugins(str(tmp_path)) == []

    def test_sorted_order(self, tmp_path):
        (tmp_path / "z-check.sh").write_text("echo z\n")
        (tmp_path / "a-check.sh").write_text("echo a\n")
        result = _load_plugins(str(tmp_path))
        assert result[0][0] == "a-check"
        assert result[1][0] == "z-check"


class TestRunCallableGate:
    def test_passing_gate(self):
        passed, output = _run_callable_gate("test", lambda: (True, "all good"))
        assert passed is True
        assert output == "all good"

    def test_failing_gate(self):
        passed, output = _run_callable_gate("test", lambda: (False, "check failed"))
        assert passed is False
        assert output == "check failed"

    def test_exception_returns_false(self):
        def bad_gate():
            raise RuntimeError("boom")

        passed, output = _run_callable_gate("test", bad_gate)
        assert passed is False
        assert "boom" in output
        assert "Gate 'test' raised" in output

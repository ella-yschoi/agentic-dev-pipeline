"""Tests for ClaudeRunner (CliClaudeRunner)."""

import subprocess
from unittest.mock import patch

import pytest

from agentic_dev_pipeline.runner import CliClaudeRunner


class TestCliClaudeRunner:
    def test_success(self):
        runner = CliClaudeRunner()
        mock_result = type("Result", (), {"returncode": 0, "stdout": "hello", "stderr": ""})()
        with patch("agentic_dev_pipeline.runner.subprocess.run", return_value=mock_result):
            output = runner.run("test prompt")
        assert output == "hello"

    def test_retry_on_nonzero_exit(self):
        runner = CliClaudeRunner()
        fail = type("R", (), {"returncode": 1, "stdout": "", "stderr": "err"})()
        ok = type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        with (
            patch("agentic_dev_pipeline.runner.subprocess.run", side_effect=[fail, ok]),
            patch("agentic_dev_pipeline.runner.time.sleep"),
        ):
            output = runner.run("test", max_retries=2)
        assert output == "ok"

    def test_timeout_retries(self):
        runner = CliClaudeRunner()
        ok = type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        with (
            patch(
                "agentic_dev_pipeline.runner.subprocess.run",
                side_effect=[subprocess.TimeoutExpired("claude", 10), ok],
            ),
            patch("agentic_dev_pipeline.runner.time.sleep"),
        ):
            output = runner.run("test", timeout=10, max_retries=2)
        assert output == "ok"

    def test_max_retries_exceeded_raises(self):
        runner = CliClaudeRunner()
        fail = type("R", (), {"returncode": 1, "stdout": "", "stderr": "err"})()
        with (
            patch("agentic_dev_pipeline.runner.subprocess.run", return_value=fail),
            patch("agentic_dev_pipeline.runner.time.sleep"),
            pytest.raises(RuntimeError, match="claude failed after 2 attempts"),
        ):
            runner.run("test", max_retries=2)

    def test_claude_not_found_raises(self):
        runner = CliClaudeRunner()
        with (
            patch(
                "agentic_dev_pipeline.runner.subprocess.run",
                side_effect=FileNotFoundError("claude"),
            ),
            pytest.raises(RuntimeError, match="not found in PATH"),
        ):
            runner.run("test")

    def test_timeout_all_retries_raises(self):
        runner = CliClaudeRunner()
        with (
            patch(
                "agentic_dev_pipeline.runner.subprocess.run",
                side_effect=subprocess.TimeoutExpired("claude", 10),
            ),
            patch("agentic_dev_pipeline.runner.time.sleep"),
            pytest.raises(RuntimeError, match="claude failed after 2 attempts"),
        ):
            runner.run("test", timeout=10, max_retries=2)

"""Integration tests for the pipeline flow using a mock claude CLI."""

import json
import os
import stat
import textwrap
from pathlib import Path

import pytest

from agentic_dev_pipeline.detect import ProjectConfig
from agentic_dev_pipeline.domain import PipelineMetrics
from agentic_dev_pipeline.pipeline import run_pipeline


@pytest.fixture
def mock_claude(tmp_path: Path) -> Path:
    """Create a mock claude CLI that succeeds and outputs a marker."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    mock = bin_dir / "claude"
    mock.write_text(textwrap.dedent("""\
        #!/bin/bash
        echo "Mock claude output: $@"
        exit 0
    """))
    mock.chmod(mock.stat().st_mode | stat.S_IEXEC)
    return bin_dir


@pytest.fixture
def mock_claude_verify_pass(tmp_path: Path) -> Path:
    """Create a mock claude that outputs TRIANGULAR_PASS for verification."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    mock = bin_dir / "claude"
    # The mock checks if the prompt mentions "discrepancy" to output TRIANGULAR_PASS
    mock.write_text(textwrap.dedent("""\
        #!/bin/bash
        if echo "$@" | grep -q "Agent C"; then
            echo "## Verdict"
            echo "TRIANGULAR_PASS"
        else
            echo "## Blind Review"
            echo "Code looks correct."
        fi
        exit 0
    """))
    mock.chmod(mock.stat().st_mode | stat.S_IEXEC)
    return bin_dir


@pytest.fixture
def pipeline_project(tmp_path: Path) -> Path:
    """Create a minimal project with prompt and requirements files."""
    (tmp_path / "PROMPT.md").write_text("# Feature: Test\nImplement a hello function.\n")
    (tmp_path / "requirements.md").write_text("# Requirements\n1. Function returns 'hello'\n")
    return tmp_path


class TestPipelineMetrics:
    def test_save_and_load(self, tmp_path):
        m = PipelineMetrics(
            started_at="2026-01-01T00:00:00",
            ended_at="2026-01-01T00:01:00",
            total_duration_s=60.0,
            total_iterations=2,
            converged=True,
        )
        path = tmp_path / "metrics.json"
        m.save(path)

        data = json.loads(path.read_text())
        assert data["converged"] is True
        assert data["total_iterations"] == 2


class TestPipelineFlow:
    def test_pipeline_no_gates_converges(
        self, pipeline_project, mock_claude_verify_pass, monkeypatch, clean_env
    ):
        """Pipeline converges when no quality gates and verification passes."""
        monkeypatch.setenv("PATH", f"{mock_claude_verify_pass}:{os.environ.get('PATH', '')}")
        monkeypatch.chdir(pipeline_project)

        config = ProjectConfig(
            project_type="python",
            lint_cmd="",
            test_cmd="",
            security_cmd="",
        )
        output_dir = pipeline_project / ".agentic-dev-pipeline"

        result = run_pipeline(
            prompt_file=pipeline_project / "PROMPT.md",
            requirements_file=pipeline_project / "requirements.md",
            output_dir=output_dir,
            max_iterations=3,
            config=config,
        )

        assert result is True
        assert (output_dir / "metrics.json").is_file()
        metrics = json.loads((output_dir / "metrics.json").read_text())
        assert metrics["converged"] is True

    def test_pipeline_gate_failure_loops(
        self, pipeline_project, mock_claude, monkeypatch, clean_env
    ):
        """Pipeline loops back when quality gate fails."""
        monkeypatch.setenv("PATH", f"{mock_claude}:{os.environ.get('PATH', '')}")
        monkeypatch.chdir(pipeline_project)

        config = ProjectConfig(
            project_type="python",
            lint_cmd="false",  # Always fails
            test_cmd="",
            security_cmd="",
        )
        output_dir = pipeline_project / ".agentic-dev-pipeline"

        result = run_pipeline(
            prompt_file=pipeline_project / "PROMPT.md",
            requirements_file=pipeline_project / "requirements.md",
            output_dir=output_dir,
            max_iterations=2,
            config=config,
        )

        assert result is False
        metrics = json.loads((output_dir / "metrics.json").read_text())
        assert metrics["converged"] is False
        assert metrics["total_iterations"] == 2

    def test_pipeline_json_logging(
        self, pipeline_project, mock_claude_verify_pass, monkeypatch, clean_env
    ):
        """Pipeline produces JSON log lines when LOG_FORMAT=json."""
        monkeypatch.setenv("PATH", f"{mock_claude_verify_pass}:{os.environ.get('PATH', '')}")
        monkeypatch.setenv("LOG_FORMAT", "json")
        monkeypatch.chdir(pipeline_project)

        config = ProjectConfig(project_type="python")
        output_dir = pipeline_project / ".agentic-dev-pipeline"

        run_pipeline(
            prompt_file=pipeline_project / "PROMPT.md",
            requirements_file=pipeline_project / "requirements.md",
            output_dir=output_dir,
            max_iterations=2,
            config=config,
        )

        log_file = output_dir / "loop-execution.log"
        assert log_file.is_file()
        # Logger lines should be valid JSON; claude output lines are plain text
        json_lines = []
        for line in log_file.read_text().strip().splitlines():
            line = line.strip()
            if line and line.startswith("{"):
                json.loads(line)  # Should not raise
                json_lines.append(line)
        # Should have logged multiple JSON events
        assert len(json_lines) > 5


    def test_pipeline_parallel_gates(
        self, pipeline_project, mock_claude_verify_pass, monkeypatch, clean_env
    ):
        """Pipeline works with parallel gate execution."""
        monkeypatch.setenv("PATH", f"{mock_claude_verify_pass}:{os.environ.get('PATH', '')}")
        monkeypatch.chdir(pipeline_project)

        config = ProjectConfig(
            project_type="python",
            lint_cmd="true",
            test_cmd="true",
            security_cmd="true",
        )
        output_dir = pipeline_project / ".agentic-dev-pipeline"

        result = run_pipeline(
            prompt_file=pipeline_project / "PROMPT.md",
            requirements_file=pipeline_project / "requirements.md",
            output_dir=output_dir,
            max_iterations=2,
            parallel_gates=True,
            config=config,
        )

        assert result is True
        metrics = json.loads((output_dir / "metrics.json").read_text())
        assert metrics["converged"] is True
        iter0 = metrics["iterations"][0]
        assert iter0["lint_result"] == "pass"
        assert iter0["test_result"] == "pass"
        assert iter0["security_result"] == "pass"

    def test_pipeline_parallel_gates_collect_all_failures(
        self, pipeline_project, mock_claude, monkeypatch, clean_env
    ):
        """Parallel gates collect ALL failures, not just the first."""
        monkeypatch.setenv("PATH", f"{mock_claude}:{os.environ.get('PATH', '')}")
        monkeypatch.chdir(pipeline_project)

        config = ProjectConfig(
            project_type="python",
            lint_cmd="echo lint-fail && false",
            test_cmd="echo test-fail && false",
            security_cmd="",
        )
        output_dir = pipeline_project / ".agentic-dev-pipeline"

        result = run_pipeline(
            prompt_file=pipeline_project / "PROMPT.md",
            requirements_file=pipeline_project / "requirements.md",
            output_dir=output_dir,
            max_iterations=1,
            parallel_gates=True,
            config=config,
        )

        assert result is False
        # Feedback should contain both failures
        feedback = (output_dir / "feedback.txt").read_text()
        assert "lint" in feedback.lower()
        assert "test" in feedback.lower()

    def test_pipeline_with_plugins(
        self, pipeline_project, mock_claude_verify_pass, tmp_path, monkeypatch, clean_env
    ):
        """Pipeline loads and runs custom plugins."""
        monkeypatch.setenv("PATH", f"{mock_claude_verify_pass}:{os.environ.get('PATH', '')}")
        monkeypatch.chdir(pipeline_project)

        # Create a plugin dir with a passing plugin
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "custom-check.sh").write_text("#!/bin/bash\necho 'custom OK'\nexit 0\n")

        config = ProjectConfig(project_type="python")
        output_dir = pipeline_project / ".agentic-dev-pipeline"

        result = run_pipeline(
            prompt_file=pipeline_project / "PROMPT.md",
            requirements_file=pipeline_project / "requirements.md",
            output_dir=output_dir,
            max_iterations=2,
            plugin_dir=str(plugin_dir),
            config=config,
        )

        assert result is True


class TestTriangularVerifyIntegration:
    def test_verify_pass(
        self, pipeline_project, mock_claude_verify_pass, monkeypatch, clean_env
    ):
        """Triangular verification passes with mock claude."""
        from agentic_dev_pipeline.verify import run_triangular_verification

        monkeypatch.setenv("PATH", f"{mock_claude_verify_pass}:{os.environ.get('PATH', '')}")
        monkeypatch.chdir(pipeline_project)

        config = ProjectConfig(
            project_type="python",
            changed_files=["src/hello.py"],
        )
        output_dir = pipeline_project / ".agentic-dev-pipeline"

        result = run_triangular_verification(
            requirements_file=pipeline_project / "requirements.md",
            output_dir=output_dir,
            config=config,
        )

        assert result is True
        assert (output_dir / "blind-review.md").is_file()
        assert (output_dir / "discrepancy-report.md").is_file()

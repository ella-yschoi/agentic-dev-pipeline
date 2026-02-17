"""Tests for the Pipeline high-level API."""

from pathlib import Path

import pytest

from agentic_dev_pipeline.api import Pipeline


class TestPipelineInit:
    def test_resolves_config_from_args(self, tmp_path, clean_env):
        p = Pipeline(
            prompt_file="P.md",
            requirements_file="R.md",
            project_root=tmp_path,
        )
        assert p.config.prompt_file == Path("P.md")
        assert p.config.requirements_file == Path("R.md")

    def test_keyword_args(self, tmp_path, clean_env):
        p = Pipeline(
            prompt_file="P.md",
            requirements_file="R.md",
            max_iterations=3,
            timeout=120,
            base_branch="develop",
            project_root=tmp_path,
        )
        assert p.config.max_iterations == 3
        assert p.config.timeout == 120
        assert p.config.base_branch == "develop"

    def test_resolves_from_pyproject(self, tmp_path, clean_env):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\n\n'
            "[tool.agentic-dev-pipeline]\n"
            'prompt-file = "PROMPT.md"\n'
            'requirements-file = "requirements.md"\n'
        )
        p = Pipeline(project_root=tmp_path)
        assert p.config.prompt_file == Path("PROMPT.md")
        assert p.config.requirements_file == Path("requirements.md")


class TestPipelineRun:
    def test_raises_without_prompt(self, tmp_path, clean_env):
        p = Pipeline(project_root=tmp_path)
        with pytest.raises(ValueError, match="prompt_file is required"):
            p.run()

    def test_raises_without_requirements(self, tmp_path, clean_env):
        p = Pipeline(prompt_file="P.md", project_root=tmp_path)
        with pytest.raises(ValueError, match="requirements_file is required"):
            p.run()


class TestPipelineAddGate:
    def test_chaining(self, tmp_path, clean_env):
        p = Pipeline(
            prompt_file="P.md",
            requirements_file="R.md",
            project_root=tmp_path,
        )
        result = p.add_gate("gate1", lambda: (True, "ok"))
        assert result is p  # chaining

    def test_multiple_gates(self, tmp_path, clean_env):
        p = Pipeline(
            prompt_file="P.md",
            requirements_file="R.md",
            project_root=tmp_path,
        )
        p.add_gate("g1", lambda: (True, "")).add_gate("g2", lambda: (True, ""))
        # Gates are stored on Pipeline, not on config


class TestPipelineDetect:
    def test_detect_returns_project_config(self, python_project, clean_env):
        p = Pipeline(project_root=python_project)
        cfg = p.detect()
        assert cfg.project_type == "python"


class TestPipelineVerify:
    def test_raises_without_requirements(self, tmp_path, clean_env):
        p = Pipeline(project_root=tmp_path)
        with pytest.raises(ValueError, match="requirements_file is required"):
            p.verify()

"""Tests for PipelineConfig hierarchical loading."""

from pathlib import Path

from agentic_dev_pipeline.config import PipelineConfig, _coerce, _normalize_toml


class TestCoerce:
    def test_int_field(self):
        assert _coerce("max_iterations", "3") == 3
        assert _coerce("timeout", "600") == 600

    def test_path_field(self):
        result = _coerce("prompt_file", "PROMPT.md")
        assert isinstance(result, Path)
        assert str(result) == "PROMPT.md"

    def test_string_field_passthrough(self):
        assert _coerce("base_branch", "develop") == "develop"


class TestNormalizeToml:
    def test_kebab_to_snake(self):
        raw = {"prompt-file": "P.md", "max-iterations": 3}
        result = _normalize_toml(raw)
        assert "prompt_file" in result
        assert "max_iterations" in result

    def test_coercion_applied(self):
        result = _normalize_toml({"max-iterations": 10, "base-branch": "dev"})
        assert result["max_iterations"] == 10
        assert result["base_branch"] == "dev"

    def test_unknown_keys_pass_through(self):
        result = _normalize_toml({"parallel-gates": True})
        # Unknown keys still normalize but won't match PipelineConfig fields
        assert result["parallel_gates"] is True


class TestFromPyproject:
    def test_reads_tool_section(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n\n'
            "[tool.agentic-dev-pipeline]\n"
            'prompt-file = "PROMPT.md"\n'
            "max-iterations = 3\n"
        )
        result = PipelineConfig.from_pyproject(tmp_path)
        assert result["prompt_file"] == Path("PROMPT.md")
        assert result["max_iterations"] == 3

    def test_missing_section_returns_empty(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\n')
        result = PipelineConfig.from_pyproject(tmp_path)
        assert result == {}

    def test_missing_file_returns_empty(self, tmp_path):
        result = PipelineConfig.from_pyproject(tmp_path)
        assert result == {}


class TestFromFile:
    def test_reads_standalone_toml(self, tmp_path):
        toml_file = tmp_path / ".agentic-dev-pipeline.toml"
        toml_file.write_text(
            'prompt-file = "PROMPT.md"\n'
            'requirements-file = "req.md"\n'
        )
        result = PipelineConfig.from_file(tmp_path)
        assert result["prompt_file"] == Path("PROMPT.md")
        assert result["requirements_file"] == Path("req.md")

    def test_missing_file_returns_empty(self, tmp_path):
        result = PipelineConfig.from_file(tmp_path)
        assert result == {}


class TestFromEnv:
    def test_reads_env_vars(self, monkeypatch):
        monkeypatch.setenv("PROMPT_FILE", "P.md")
        monkeypatch.setenv("MAX_ITERATIONS", "10")
        result = PipelineConfig.from_env()
        assert result["prompt_file"] == Path("P.md")
        assert result["max_iterations"] == 10

    def test_missing_env_returns_empty(self, clean_env, monkeypatch):
        monkeypatch.delenv("PROMPT_FILE", raising=False)
        monkeypatch.delenv("REQUIREMENTS_FILE", raising=False)
        monkeypatch.delenv("MAX_ITERATIONS", raising=False)
        result = PipelineConfig.from_env()
        assert result == {}


class TestResolve:
    def test_defaults(self, tmp_path, clean_env):
        cfg = PipelineConfig.resolve(project_root=tmp_path)
        assert cfg.max_iterations == 5
        assert cfg.timeout == 300
        assert cfg.prompt_file is None
        assert cfg.base_branch == "main"

    def test_explicit_overrides_all(self, tmp_path, clean_env, monkeypatch):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\n\n'
            "[tool.agentic-dev-pipeline]\n"
            "max-iterations = 10\n"
        )
        monkeypatch.setenv("MAX_ITERATIONS", "20")
        cfg = PipelineConfig.resolve({"max_iterations": 3}, project_root=tmp_path)
        assert cfg.max_iterations == 3

    def test_pyproject_overrides_file(self, tmp_path, clean_env):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\n\n'
            "[tool.agentic-dev-pipeline]\n"
            "max-iterations = 7\n"
        )
        (tmp_path / ".agentic-dev-pipeline.toml").write_text("max-iterations = 3\n")
        cfg = PipelineConfig.resolve(project_root=tmp_path)
        assert cfg.max_iterations == 7

    def test_file_overrides_env(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.setenv("MAX_ITERATIONS", "20")
        (tmp_path / ".agentic-dev-pipeline.toml").write_text("max-iterations = 3\n")
        cfg = PipelineConfig.resolve(project_root=tmp_path)
        assert cfg.max_iterations == 3

    def test_env_used_when_no_files(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.setenv("MAX_ITERATIONS", "8")
        cfg = PipelineConfig.resolve(project_root=tmp_path)
        assert cfg.max_iterations == 8

    def test_unknown_toml_keys_ignored(self, tmp_path, clean_env):
        """Keys not in PipelineConfig (e.g. parallel-gates) are silently ignored."""
        (tmp_path / ".agentic-dev-pipeline.toml").write_text(
            'prompt-file = "P.md"\nparallel-gates = true\n'
        )
        cfg = PipelineConfig.resolve(project_root=tmp_path)
        assert cfg.prompt_file == Path("P.md")
        assert not hasattr(cfg, "parallel_gates")

from __future__ import annotations

import os
from pathlib import Path

from agentic_dev_pipeline.config import PipelineConfig
from agentic_dev_pipeline.detect import ProjectConfig, detect_all
from agentic_dev_pipeline.domain import GateFunction
from agentic_dev_pipeline.log import Logger
from agentic_dev_pipeline.pipeline import run_pipeline
from agentic_dev_pipeline.verify import run_triangular_verification


class Pipeline:
    """Fluent interface for configuring and running the agentic dev pipeline."""

    def __init__(
        self,
        prompt_file: str | Path | None = None,
        requirements_file: str | Path | None = None,
        *,
        max_iterations: int | None = None,
        timeout: int | None = None,
        base_branch: str | None = None,
        project_root: str | Path | None = None,
    ) -> None:
        root = Path(project_root) if project_root else Path.cwd()

        # Build explicit overrides from constructor args
        explicit: dict[str, object] = {}
        if prompt_file is not None:
            explicit["prompt_file"] = Path(prompt_file)
        if requirements_file is not None:
            explicit["requirements_file"] = Path(requirements_file)
        if max_iterations is not None:
            explicit["max_iterations"] = max_iterations
        if timeout is not None:
            explicit["timeout"] = timeout
        if base_branch is not None:
            explicit["base_branch"] = base_branch

        self._config = PipelineConfig.resolve(explicit, project_root=root)
        self._project_root = root
        self._custom_gates: list[tuple[str, GateFunction]] = []

    @property
    def config(self) -> PipelineConfig:
        return self._config

    def add_gate(self, name: str, func: GateFunction) -> Pipeline:
        """Add a custom Python callable gate. Returns self for chaining."""
        self._custom_gates.append((name, func))
        return self

    def run(self) -> bool:
        """Run the full pipeline. Returns True if converged."""
        cfg = self._config
        if cfg.prompt_file is None:
            raise ValueError(
                "prompt_file is required. Pass it to Pipeline() or set it in "
                "pyproject.toml / .agentic-dev-pipeline.toml / PROMPT_FILE env var."
            )
        if cfg.requirements_file is None:
            raise ValueError(
                "requirements_file is required. Pass it to Pipeline() or set it in "
                "pyproject.toml / .agentic-dev-pipeline.toml / REQUIREMENTS_FILE env var."
            )

        output_dir, logger, project_config = self._prepare()

        return run_pipeline(
            prompt_file=Path(cfg.prompt_file),
            requirements_file=Path(cfg.requirements_file),
            output_dir=output_dir,
            max_iterations=cfg.max_iterations,
            claude_timeout=cfg.timeout,
            max_retries=cfg.max_retries,
            config=project_config,
            logger=logger,
            custom_gates=self._custom_gates or None,
        )

    def verify(self) -> bool:
        """Run triangular verification only. Returns True if passed."""
        cfg = self._config
        if cfg.requirements_file is None:
            raise ValueError(
                "requirements_file is required for verification."
            )

        output_dir, logger, project_config = self._prepare()

        return run_triangular_verification(
            requirements_file=Path(cfg.requirements_file),
            output_dir=output_dir,
            config=project_config,
            timeout=cfg.timeout,
            max_retries=cfg.max_retries,
            logger=logger,
        )

    def detect(self) -> ProjectConfig:
        """Run project detection only. Returns detected config."""
        return detect_all(
            project_root=self._project_root,
            base_branch=self._config.base_branch,
        )

    def _prepare(self) -> tuple[Path, Logger, ProjectConfig]:
        """Create output_dir, logger, and project_config once."""
        output_dir = Path(os.environ.get("OUTPUT_DIR", ".agentic-dev-pipeline"))
        logger = Logger(
            log_file=output_dir / "loop-execution.log",
            json_mode=os.environ.get("LOG_FORMAT", "").lower() == "json",
        )
        project_config = detect_all(
            project_root=self._project_root,
            base_branch=self._config.base_branch,
        )
        return output_dir, logger, project_config

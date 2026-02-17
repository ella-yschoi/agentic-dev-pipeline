from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentic-dev-pipeline")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from agentic_dev_pipeline.api import Pipeline
from agentic_dev_pipeline.detect import ProjectConfig, detect_all
from agentic_dev_pipeline.domain import GateFunction, GateStatus
from agentic_dev_pipeline.log import Logger
from agentic_dev_pipeline.pipeline import run_pipeline
from agentic_dev_pipeline.runner import ClaudeRunner
from agentic_dev_pipeline.verify import run_triangular_verification

__all__ = [
    "ClaudeRunner",
    "GateFunction",
    "GateStatus",
    "Logger",
    "Pipeline",
    "ProjectConfig",
    "__version__",
    "detect_all",
    "run_pipeline",
    "run_triangular_verification",
]

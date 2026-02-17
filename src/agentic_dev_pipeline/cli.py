from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from agentic_dev_pipeline import __version__
from agentic_dev_pipeline.config import PipelineConfig
from agentic_dev_pipeline.detect import detect_all
from agentic_dev_pipeline.init_cmd import run_init
from agentic_dev_pipeline.log import Logger
from agentic_dev_pipeline.pipeline import run_pipeline
from agentic_dev_pipeline.verify import run_triangular_verification


def _positive_int(value: str) -> int:
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {n}")
    return n


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-dev-pipeline",
        description=(
            "Agentic dev pipeline: code → quality gates "
            "→ triangular verification → self-correction loop"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    # --- run ---
    run_parser = subparsers.add_parser("run", help="Run the full pipeline")
    run_parser.add_argument(
        "--prompt",
        default=None,
        help="Path to prompt file (default: config file or $PROMPT_FILE)",
    )
    run_parser.add_argument(
        "--requirements",
        default=None,
        help="Path to requirements file (default: config file or $REQUIREMENTS_FILE)",
    )
    run_parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: .agentic-dev-pipeline/)",
    )
    run_parser.add_argument(
        "--max-iterations",
        type=_positive_int,
        default=None,
        help="Maximum loop iterations (default: 5)",
    )
    run_parser.add_argument(
        "--timeout",
        type=_positive_int,
        default=None,
        help="Timeout per claude call in seconds (default: 300)",
    )
    run_parser.add_argument(
        "--max-retries",
        type=_positive_int,
        default=None,
        help="Max retries per claude call (default: 2)",
    )
    run_parser.add_argument(
        "--base-branch",
        default=None,
        help="Git base branch (default: main)",
    )
    run_parser.add_argument(
        "--webhook-url",
        default=None,
        help="Webhook URL for notifications (default: $WEBHOOK_URL)",
    )
    run_parser.add_argument(
        "--parallel-gates",
        action="store_true",
        default=None,
        help="Run quality gates in parallel (default: $PARALLEL_GATES)",
    )
    run_parser.add_argument(
        "--plugin-dir",
        default=None,
        help="Directory with custom gate plugins (default: $PLUGIN_DIR)",
    )

    # --- verify ---
    verify_parser = subparsers.add_parser("verify", help="Run triangular verification only")
    verify_parser.add_argument(
        "--requirements",
        default=None,
        help="Path to requirements file (default: $REQUIREMENTS_FILE)",
    )
    verify_parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: .agentic-dev-pipeline/)",
    )
    verify_parser.add_argument(
        "--base-branch",
        default=None,
        help="Git base branch (default: main)",
    )
    verify_parser.add_argument(
        "--timeout",
        type=_positive_int,
        default=None,
        help="Timeout per claude call in seconds (default: 300 or $CLAUDE_TIMEOUT)",
    )
    verify_parser.add_argument(
        "--max-retries",
        type=_positive_int,
        default=None,
        help="Max retries per claude call (default: 2 or $MAX_RETRIES)",
    )

    # --- detect ---
    subparsers.add_parser("detect", help="Print detected project configuration")

    # --- init ---
    init_parser = subparsers.add_parser("init", help="Initialize pipeline config in project")
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing files"
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "detect":
        config = detect_all()
        print(config.print_config())
        sys.exit(0)

    if args.command == "init":
        actions = run_init(force=args.force)
        for action in actions:
            print(action)
        print("\nDone! Edit PROMPT.md and requirements.md, then run:")
        print("  agentic-dev-pipeline run")
        sys.exit(0)

    if args.command == "verify":
        requirements = args.requirements or os.environ.get("REQUIREMENTS_FILE")
        if not requirements:
            print(
                "ERROR: --requirements or REQUIREMENTS_FILE is required.",
                file=sys.stderr,
            )
            sys.exit(1)

        req_path = Path(requirements)
        if not req_path.is_file():
            print(f"ERROR: Requirements file not found: {req_path}", file=sys.stderr)
            sys.exit(1)

        output_dir = Path(
            args.output_dir or os.environ.get("OUTPUT_DIR", ".agentic-dev-pipeline")
        )
        base_branch = args.base_branch or os.environ.get("BASE_BRANCH", "main")
        timeout = args.timeout or int(os.environ.get("CLAUDE_TIMEOUT", "300"))
        max_retries = args.max_retries or int(os.environ.get("MAX_RETRIES", "2"))
        logger = Logger(log_file=output_dir / "loop-execution.log")

        passed = run_triangular_verification(
            requirements_file=req_path,
            output_dir=output_dir,
            config=detect_all(base_branch=base_branch),
            timeout=timeout,
            max_retries=max_retries,
            logger=logger,
        )
        sys.exit(0 if passed else 1)

    if args.command == "run":
        # Resolve shared config: CLI flags > pyproject.toml > .toml > env > defaults
        explicit: dict[str, object] = {}
        if args.prompt is not None:
            explicit["prompt_file"] = Path(args.prompt)
        if args.requirements is not None:
            explicit["requirements_file"] = Path(args.requirements)
        if args.max_iterations is not None:
            explicit["max_iterations"] = args.max_iterations
        if args.timeout is not None:
            explicit["timeout"] = args.timeout
        if args.max_retries is not None:
            explicit["max_retries"] = args.max_retries
        if args.base_branch is not None:
            explicit["base_branch"] = args.base_branch

        cfg = PipelineConfig.resolve(explicit)

        if cfg.prompt_file is None:
            print(
                "ERROR: --prompt, config file, or PROMPT_FILE env var is required.",
                file=sys.stderr,
            )
            sys.exit(1)

        prompt_path = Path(cfg.prompt_file)
        if not prompt_path.is_file():
            print(f"ERROR: Prompt file not found: {prompt_path}", file=sys.stderr)
            sys.exit(1)

        if cfg.requirements_file is None:
            print(
                "ERROR: --requirements, config file, or REQUIREMENTS_FILE "
                "env var is required.",
                file=sys.stderr,
            )
            sys.exit(1)

        req_path = Path(cfg.requirements_file)
        if not req_path.is_file():
            print(f"ERROR: Requirements file not found: {req_path}", file=sys.stderr)
            sys.exit(1)

        if prompt_path.stat().st_size == 0:
            print(f"ERROR: Prompt file is empty: {prompt_path}", file=sys.stderr)
            sys.exit(1)

        if req_path.stat().st_size == 0:
            print(f"ERROR: Requirements file is empty: {req_path}", file=sys.stderr)
            sys.exit(1)

        # CLI-only options: resolved from flags / env vars directly
        output_dir = Path(
            args.output_dir or os.environ.get("OUTPUT_DIR", ".agentic-dev-pipeline")
        )
        webhook_url = args.webhook_url or os.environ.get("WEBHOOK_URL", "")

        logger = Logger(log_file=output_dir / "loop-execution.log")
        project_config = detect_all(base_branch=cfg.base_branch)

        converged = run_pipeline(
            prompt_file=prompt_path,
            requirements_file=req_path,
            output_dir=output_dir,
            max_iterations=cfg.max_iterations,
            claude_timeout=cfg.timeout,
            max_retries=cfg.max_retries,
            webhook_url=webhook_url,
            parallel_gates=args.parallel_gates,
            plugin_dir=args.plugin_dir,
            config=project_config,
            logger=logger,
        )

        sys.exit(0 if converged else 1)

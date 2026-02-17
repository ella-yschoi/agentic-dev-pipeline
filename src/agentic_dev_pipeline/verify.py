from __future__ import annotations

import signal
import sys
from pathlib import Path

from agentic_dev_pipeline.detect import ProjectConfig, detect_all
from agentic_dev_pipeline.domain import TRIANGULAR_PASS_MARKER
from agentic_dev_pipeline.log import Logger
from agentic_dev_pipeline.runner import ClaudeRunner, CliClaudeRunner


def run_triangular_verification(
    requirements_file: Path,
    output_dir: Path,
    config: ProjectConfig | None = None,
    timeout: int = 300,
    max_retries: int = 2,
    logger: Logger | None = None,
    runner: ClaudeRunner | None = None,
) -> bool:
    """Run triangular verification. Returns True if TRIANGULAR_PASS found.

    Args:
        requirements_file: Path to requirements document (source of truth).
        output_dir: Directory for output artifacts.
        config: Project configuration. Auto-detected if None.
        timeout: Timeout per claude call in seconds.
        max_retries: Max retries per claude call.
        logger: Logger instance.
        runner: ClaudeRunner instance. Defaults to CliClaudeRunner.

    Returns:
        True if verification passed, False otherwise.
    """
    if logger is None:
        logger = Logger()

    cfg = config or detect_all()
    _runner = runner or CliClaudeRunner()

    output_dir.mkdir(parents=True, exist_ok=True)
    blind_review_file = output_dir / "blind-review.md"
    discrepancy_file = output_dir / "discrepancy-report.md"

    # Build context file list for Agent B
    context_lines: list[str] = []
    if cfg.instruction_files:
        context_lines.append(f"Project rules/conventions: {' '.join(cfg.instruction_files)}")
    if cfg.design_docs:
        context_lines.append(f"Design documents: {' '.join(cfg.design_docs)}")
    context_section = "\n".join(context_lines)

    changed_section = "\n".join(cfg.changed_files)

    logger.info("Started triangular verification")
    logger.info(f"Requirements: {requirements_file}")
    logger.info(f"Changed files: {len(cfg.changed_files)}")

    # --- Agent B: Blind Review ---
    logger.info("Phase B: Blind review (read code only, describe behavior)")

    context_instruction = ""
    if context_section:
        context_instruction = (
            f"Read the following files for project context:\n{context_section}\n\n"
        )

    agent_b_prompt = f"""{context_instruction}\
Do NOT read any requirements document ({requirements_file}).

The following files were recently changed or created:
{changed_section}

For each file:
1. Describe what this code does (behavior and intent, not just structure)
2. List any convention/rule violations found in the project rules
3. List potential issues, edge cases, or bugs

Output your analysis as structured markdown."""

    output_b = _runner.run(agent_b_prompt, timeout=timeout, max_retries=max_retries, logger=logger)
    blind_review_file.write_text(output_b)
    logger.info(f"Blind review saved to {blind_review_file}")

    # --- Agent C: Discrepancy Report ---
    logger.info("Phase C: Discrepancy report (requirements vs blind review)")

    agent_c_prompt = f"""\
You are Agent C in a triangular verification process.

Read these two documents carefully:
1. {requirements_file} (original requirements — the source of truth)
2. {blind_review_file} (blind code analysis by another agent)

Do NOT read any code files directly.

Compare them and produce a discrepancy report with these sections:

## Requirements Met
List each requirement confirmed by the blind review, with evidence.

## Requirements Missed
Requirements present in the requirements doc but NOT reflected in the blind review.

## Extra Behavior
Behavior described in the blind review but NOT in the requirements.

## Potential Bugs
Where the blind review contradicts or conflicts with requirements.

## Verdict
If ALL requirements are met and no critical issues found, output exactly on its own line:
{TRIANGULAR_PASS_MARKER}

Otherwise, list each issue that must be fixed."""

    output_c = _runner.run(agent_c_prompt, timeout=timeout, max_retries=max_retries, logger=logger)
    discrepancy_file.write_text(output_c)
    logger.info(f"Discrepancy report saved to {discrepancy_file}")

    report_text = discrepancy_file.read_text()
    passed = TRIANGULAR_PASS_MARKER in report_text

    if passed:
        logger.info("RESULT: PASS")
    else:
        logger.info(f"RESULT: FAIL — issues found in {discrepancy_file}")

    return passed


def main() -> None:
    """CLI entry point for standalone triangular verification."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Triangular verification: blind review + discrepancy report"
    )
    parser.add_argument(
        "--requirements",
        default=None,
        help="Path to requirements file (default: $REQUIREMENTS_FILE)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: .agentic-dev-pipeline/)",
    )
    parser.add_argument(
        "--base-branch",
        default=None,
        help="Git base branch (default: main)",
    )
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per claude call")
    parser.add_argument("--max-retries", type=int, default=2, help="Max retries per claude call")
    args = parser.parse_args()

    requirements = args.requirements or os.environ.get("REQUIREMENTS_FILE")
    if not requirements:
        print("ERROR: --requirements or REQUIREMENTS_FILE is required.", file=sys.stderr)
        sys.exit(1)

    req_path = Path(requirements)
    if not req_path.is_file():
        print(f"ERROR: Requirements file not found: {req_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir or os.environ.get("OUTPUT_DIR", ".agentic-dev-pipeline"))
    base_branch = args.base_branch or os.environ.get("BASE_BRANCH", "main")

    logger = Logger()
    config = detect_all(base_branch=base_branch)

    # Signal handling
    def _signal_handler(signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.warn(f"Received {sig_name}, shutting down...")
        sys.exit(128 + signum)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    passed = run_triangular_verification(
        requirements_file=req_path,
        output_dir=output_dir,
        config=config,
        timeout=args.timeout,
        max_retries=args.max_retries,
        logger=logger,
    )

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

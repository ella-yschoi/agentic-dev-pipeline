from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import time
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agentic_dev_pipeline.detect import ProjectConfig, detect_all
from agentic_dev_pipeline.domain import (
    GateResult,
    GateStatus,
    IterationMetrics,
    IterationOutcome,
    PipelineMetrics,
)
from agentic_dev_pipeline.log import Logger
from agentic_dev_pipeline.runner import ClaudeRunner, CliClaudeRunner
from agentic_dev_pipeline.verify import run_triangular_verification

_GATE_OUTPUT_LIMIT = 500

_UNSAFE_PATTERN = re.compile(r"\$\(|`|;\s*rm\s|&&\s*rm\s|>\s*/dev/")


def _is_safe_command(cmd: str) -> bool:
    """Return True if cmd does not contain obvious injection patterns."""
    return not _UNSAFE_PATTERN.search(cmd)


def _run_gate_command(cmd: str, timeout: int = 300) -> tuple[bool, str]:
    """Run a quality gate command safely. Returns (passed, output)."""
    if not _is_safe_command(cmd):
        return False, f"BLOCKED: command contains unsafe patterns: {cmd}"

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s: {cmd}"
    except Exception as e:
        return False, f"Command failed: {e}"


def _load_plugins(plugin_dir: str | None = None) -> list[tuple[str, str]]:
    """Load custom quality gate plugins from PLUGIN_DIR.

    Each plugin is a .sh or .py file. Returns list of (name, command).
    """
    pdir = plugin_dir or os.environ.get("PLUGIN_DIR", "")
    if not pdir:
        return []

    path = Path(pdir)
    if not path.is_dir():
        return []

    plugins: list[tuple[str, str]] = []
    for f in sorted(path.iterdir()):
        if f.suffix == ".sh" and f.is_file():
            plugins.append((f.stem, f"bash {f}"))
        elif f.suffix == ".py" and f.is_file():
            plugins.append((f.stem, f"python3 {f}"))
    return plugins


def _run_callable_gate(name: str, func: Callable[[], tuple[bool, str]]) -> tuple[bool, str]:
    """Run a Python callable gate. Returns (passed, output)."""
    try:
        return func()
    except Exception as e:
        return False, f"Gate '{name}' raised: {e}"


def _send_webhook(url: str, payload: dict[str, object]) -> None:
    """Send webhook notification. Best-effort, never raises."""
    try:
        body = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _run_implementation_phase(
    *,
    iteration: int,
    prompt_file: Path,
    feedback_file: Path,
    runner: ClaudeRunner,
    log_path: Path,
    timeout: int,
    max_retries: int,
    logger: Logger,
) -> None:
    """Phase 1: Claude implementation/fix. Runner output appended to log file."""
    if iteration == 1:
        prompt_text = prompt_file.read_text()
    else:
        feedback = (
            feedback_file.read_text()
            if feedback_file.is_file()
            else "No specific feedback available"
        )
        prompt_text = f"""\
Read {prompt_file} for the full requirements.

Previous iteration ({iteration - 1}) failed with this feedback:
---
{feedback}
---

Fix the issues described above. Do NOT start from scratch.
Read the existing code first, then make targeted fixes only.
After fixing, verify your changes match the requirements."""

    output = runner.run(prompt_text, timeout=timeout, max_retries=max_retries, logger=logger)
    with log_path.open("a") as f:
        f.write(output)


def _run_quality_gates(
    *,
    gates: list[tuple[str, str]],
    callable_gates: list[tuple[str, Callable[[], tuple[bool, str]]]],
    use_parallel: bool,
    timeout: int,
    logger: Logger,
) -> tuple[bool, str, list[GateResult]]:
    """Phase 2: Run all quality gates. Returns (all_passed, failure_output, results)."""
    results: list[GateResult] = []
    total_gates = len(gates) + len(callable_gates)

    if not total_gates:
        logger.info("[Phase 2] No quality gates configured — skipping")
        return True, "", results

    if use_parallel:
        return _run_gates_parallel(
            gates=gates, callable_gates=callable_gates, timeout=timeout, logger=logger,
        )

    return _run_gates_sequential(
        gates=gates, callable_gates=callable_gates, timeout=timeout, logger=logger,
    )


def _run_gates_parallel(
    *,
    gates: list[tuple[str, str]],
    callable_gates: list[tuple[str, Callable[[], tuple[bool, str]]]],
    timeout: int,
    logger: Logger,
) -> tuple[bool, str, list[GateResult]]:
    total = len(gates) + len(callable_gates)
    logger.info(f"[Phase 2] Running {total} gates in parallel")
    results: list[GateResult] = []
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        future_map: dict[object, str] = {}
        for name, cmd in gates:
            future_map[executor.submit(_run_gate_command, cmd, timeout)] = name
        for cname, cfunc in callable_gates:
            future_map[executor.submit(_run_callable_gate, cname, cfunc)] = f"callable:{cname}"

        for future in as_completed(future_map):
            name = future_map[future]
            passed, output = future.result()
            status = GateStatus.PASS if passed else GateStatus.FAIL
            results.append(GateResult(name=name, status=status, output=output[:_GATE_OUTPUT_LIMIT]))

            if passed:
                logger.info(f"[Phase 2] {name}: PASS")
            else:
                logger.info(f"[Phase 2] {name}: FAIL")
                failures.append(f"{name} FAILED:\n{output}")

    if failures:
        return False, "\n\n".join(failures), results
    return True, "", results


def _run_gates_sequential(
    *,
    gates: list[tuple[str, str]],
    callable_gates: list[tuple[str, Callable[[], tuple[bool, str]]]],
    timeout: int,
    logger: Logger,
) -> tuple[bool, str, list[GateResult]]:
    results: list[GateResult] = []
    gate_pass = True
    gate_output = ""

    for name, cmd in gates:
        if not gate_pass:
            break
        logger.info(f"[Phase 2] Running {name}: {cmd}")
        passed, output = _run_gate_command(cmd, timeout)
        status = GateStatus.PASS if passed else GateStatus.FAIL
        results.append(GateResult(name=name, status=status, output=output[:_GATE_OUTPUT_LIMIT]))

        if passed:
            logger.info(f"[Phase 2] {name}: PASS")
        else:
            logger.info(f"[Phase 2] {name}: FAIL")
            gate_output = f"{name} ({cmd}) FAILED:\n{output}"
            gate_pass = False

    for cname, cfunc in callable_gates:
        if not gate_pass:
            break
        logger.info(f"[Phase 2] Running callable:{cname}")
        passed, output = _run_callable_gate(cname, cfunc)
        status = GateStatus.PASS if passed else GateStatus.FAIL
        results.append(
            GateResult(name=f"callable:{cname}", status=status, output=output[:_GATE_OUTPUT_LIMIT])
        )

        if passed:
            logger.info(f"[Phase 2] callable:{cname}: PASS")
        else:
            logger.info(f"[Phase 2] callable:{cname}: FAIL")
            gate_output = f"callable:{cname} FAILED:\n{output}"
            gate_pass = False

    return gate_pass, gate_output, results


def run_pipeline(
    prompt_file: Path,
    requirements_file: Path,
    output_dir: Path | None = None,
    max_iterations: int = 5,
    claude_timeout: int = 300,
    max_retries: int = 2,
    webhook_url: str = "",
    parallel_gates: bool | None = None,
    plugin_dir: str | None = None,
    config: ProjectConfig | None = None,
    logger: Logger | None = None,
    custom_gates: list[tuple[str, Callable[[], tuple[bool, str]]]] | None = None,
    runner: ClaudeRunner | None = None,
) -> bool:
    """Run the full agentic dev pipeline.

    Args:
        parallel_gates: Run lint/test/security in parallel. Default: $PARALLEL_GATES env.
        plugin_dir: Directory with custom gate plugins (.sh/.py). Default: $PLUGIN_DIR env.
        custom_gates: Python callable gates as (name, func) pairs. Each func returns (passed, msg).
        runner: ClaudeRunner instance. Defaults to CliClaudeRunner.

    Returns True if the pipeline converged (all gates + verification passed).
    """
    out = output_dir or Path(os.environ.get("OUTPUT_DIR", ".agentic-dev-pipeline"))
    out.mkdir(parents=True, exist_ok=True)

    if logger is None:
        logger = Logger(log_file=out / "loop-execution.log")

    cfg = config or detect_all()
    _runner = runner or CliClaudeRunner()
    feedback_file = out / "feedback.txt"
    metrics = PipelineMetrics(started_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    use_parallel = parallel_gates if parallel_gates is not None else (
        os.environ.get("PARALLEL_GATES", "").lower() in ("true", "1", "yes")
    )
    plugins = _load_plugins(plugin_dir)

    # Unset CLAUDECODE to allow nested calls
    os.environ.pop("CLAUDECODE", None)

    shutdown_requested = False

    def _signal_handler(signum: int, _frame: object) -> None:
        nonlocal shutdown_requested
        sig_name = signal.Signals(signum).name
        logger.warn(f"Received {sig_name}, will exit after current phase...")
        shutdown_requested = True

    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    start_time = time.time()

    logger.info("=== Agentic Dev Pipeline ===")
    logger.info(cfg.print_config())
    logger.info(f"Max iterations: {max_iterations}")
    logger.info(f"Prompt: {prompt_file}")
    logger.info(f"Requirements: {requirements_file}")
    logger.info(f"Output dir: {out}")
    logger.info(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    if not shutil.which("claude"):
        logger.error("'claude' CLI not found in PATH. Install Claude Code first.")
        return False

    converged = False

    try:
        for iteration in range(1, max_iterations + 1):
            if shutdown_requested:
                logger.warn("Shutdown requested, stopping pipeline")
                break

            iter_start = time.time()
            iter_metrics = IterationMetrics(iteration=iteration)

            logger.info(f"--- Iteration {iteration} / {max_iterations} ---")

            # Phase 1: Implementation (or fix)
            logger.phase_start("phase1_implement", iteration=iteration)

            _run_implementation_phase(
                iteration=iteration,
                prompt_file=prompt_file,
                feedback_file=feedback_file,
                runner=_runner,
                log_path=out / "loop-execution.log",
                timeout=claude_timeout,
                max_retries=max_retries,
                logger=logger,
            )

            iter_metrics.phase1_done = True
            logger.phase_end("phase1_implement", "completed", iteration=iteration)

            if shutdown_requested:
                break

            # Phase 2: Quality Gates
            logger.phase_start("phase2_quality_gates", iteration=iteration)

            gates: list[tuple[str, str]] = []
            if cfg.lint_cmd:
                gates.append(("lint", cfg.lint_cmd))
            if cfg.test_cmd:
                gates.append(("test", cfg.test_cmd))
            if cfg.security_cmd:
                gates.append(("security", cfg.security_cmd))
            for plugin_name, plugin_cmd in plugins:
                gates.append((f"plugin:{plugin_name}", plugin_cmd))

            callable_gates = custom_gates or []

            gate_pass, gate_output, gate_results = _run_quality_gates(
                gates=gates,
                callable_gates=callable_gates,
                use_parallel=use_parallel,
                timeout=claude_timeout,
                logger=logger,
            )
            iter_metrics.gate_results = gate_results

            if not gate_pass:
                feedback_file.write_text(gate_output)
                iter_metrics.outcome = IterationOutcome.GATE_FAIL
                iter_metrics.duration_s = round(time.time() - iter_start, 2)
                metrics.iterations.append(iter_metrics)
                logger.phase_end("phase2_quality_gates", "fail", iteration=iteration)
                logger.info(f"[Phase 2] FAILED — looping back (took {iter_metrics.duration_s}s)")
                logger.info("")
                continue

            logger.phase_end("phase2_quality_gates", "pass", iteration=iteration)

            if shutdown_requested:
                break

            # Phase 3: Triangular Verification
            logger.phase_start("phase3_triangular_verify", iteration=iteration)

            passed = run_triangular_verification(
                requirements_file=requirements_file,
                output_dir=out,
                config=cfg,
                timeout=claude_timeout,
                max_retries=max_retries,
                logger=logger,
                runner=_runner,
            )

            if passed:
                iter_metrics.verification_status = GateStatus.PASS
                logger.phase_end("phase3_triangular_verify", "pass", iteration=iteration)
            else:
                iter_metrics.verification_status = GateStatus.FAIL
                discrepancy_file = out / "discrepancy-report.md"
                if discrepancy_file.is_file():
                    feedback_file.write_text(discrepancy_file.read_text())
                else:
                    feedback_file.write_text(
                        "Triangular verification failed but no discrepancy report found."
                    )
                iter_metrics.outcome = IterationOutcome.VERIFY_FAIL
                iter_metrics.duration_s = round(time.time() - iter_start, 2)
                metrics.iterations.append(iter_metrics)
                logger.phase_end("phase3_triangular_verify", "fail", iteration=iteration)
                logger.info(f"[Phase 3] FAILED — looping back (took {iter_metrics.duration_s}s)")
                logger.info("")
                continue

            # Phase 4: Complete
            iter_metrics.outcome = IterationOutcome.PASS
            iter_metrics.duration_s = round(time.time() - iter_start, 2)
            metrics.iterations.append(iter_metrics)

            total_time = round(time.time() - start_time, 2)

            logger.info("")
            logger.info("=== LOOP_COMPLETE ===")
            logger.info(f"Finished in {iteration} iteration(s), total {total_time}s")
            logger.info(f"Ended: {time.strftime('%Y-%m-%d %H:%M:%S')}")

            feedback_file.unlink(missing_ok=True)
            converged = True
            break

    finally:
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)

        total_time = round(time.time() - start_time, 2)
        metrics.ended_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        metrics.total_duration_s = total_time
        metrics.total_iterations = len(metrics.iterations)
        metrics.converged = converged
        metrics.save(out / "metrics.json")

        if webhook_url:
            _send_webhook(webhook_url, {
                "pipeline": "agentic-dev-pipeline",
                "converged": converged,
                "iterations": metrics.total_iterations,
                "duration_s": total_time,
            })

    if not converged:
        logger.info("")
        logger.info("=== MAX ITERATIONS REACHED ===")
        logger.info(f"Completed {max_iterations} iterations without full convergence.")
        logger.info(f"Total time: {total_time}s")
        logger.info(f"Review remaining issues in: {feedback_file}")
        logger.info(f"Review full log in: {out / 'loop-execution.log'}")

    return converged

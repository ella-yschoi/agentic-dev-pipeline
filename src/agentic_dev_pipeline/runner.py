from __future__ import annotations

import subprocess
import time
from typing import Protocol

from agentic_dev_pipeline.log import Logger


class ClaudeRunner(Protocol):
    def run(
        self,
        prompt: str,
        *,
        timeout: int = 300,
        max_retries: int = 2,
        logger: Logger | None = None,
    ) -> str: ...


class CliClaudeRunner:
    """Run claude CLI via subprocess with retry and backoff."""

    def run(
        self,
        prompt: str,
        *,
        timeout: int = 300,
        max_retries: int = 2,
        logger: Logger | None = None,
    ) -> str:
        for attempt in range(1, max_retries + 1):
            try:
                result = subprocess.run(
                    ["claude", "--print", "-p", prompt],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if result.returncode == 0:
                    return result.stdout
                if logger:
                    logger.warn(
                        f"claude exited with code {result.returncode} (attempt {attempt})"
                    )
                if result.stderr and logger:
                    logger.warn(f"stderr: {result.stderr[:500]}")
            except subprocess.TimeoutExpired:
                if logger:
                    logger.warn(f"claude timed out after {timeout}s (attempt {attempt})")
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "'claude' CLI not found in PATH. Install Claude Code first."
                ) from exc

            if attempt < max_retries:
                backoff = 2**attempt
                if logger:
                    logger.info(f"Retrying in {backoff}s...")
                time.sleep(backoff)

        raise RuntimeError(f"claude failed after {max_retries} attempts")

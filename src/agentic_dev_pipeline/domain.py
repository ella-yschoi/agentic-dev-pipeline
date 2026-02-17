from __future__ import annotations

import enum
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


class GateStatus(enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class IterationOutcome(enum.Enum):
    PASS = "pass"
    GATE_FAIL = "gate_fail"
    VERIFY_FAIL = "verify_fail"


TRIANGULAR_PASS_MARKER = "TRIANGULAR_PASS"

GateFunction = Callable[[], tuple[bool, str]]


@dataclass
class GateResult:
    name: str = ""
    status: GateStatus = GateStatus.SKIPPED
    output: str = ""
    duration_s: float = 0.0


@dataclass
class IterationMetrics:
    iteration: int = 0
    duration_s: float = 0.0
    phase1_done: bool = False
    gate_results: list[GateResult] = field(default_factory=list)
    verification_status: GateStatus = GateStatus.SKIPPED
    outcome: IterationOutcome | None = None

    @property
    def lint_result(self) -> str:
        return self._gate_status("lint")

    @property
    def test_result(self) -> str:
        return self._gate_status("test")

    @property
    def security_result(self) -> str:
        return self._gate_status("security")

    @property
    def plugin_results(self) -> list[dict[str, object]]:
        return [
            {
                "name": g.name,
                "result": g.status.value,
                "output": g.output,
                "duration_s": g.duration_s,
            }
            for g in self.gate_results
            if g.name not in ("lint", "test", "security")
        ]

    @property
    def verification_result(self) -> str:
        return self.verification_status.value

    def to_dict(self) -> dict[str, object]:
        return {
            "iteration": self.iteration,
            "duration_s": self.duration_s,
            "phase1_done": self.phase1_done,
            "lint_result": self.lint_result,
            "test_result": self.test_result,
            "security_result": self.security_result,
            "plugin_results": self.plugin_results,
            "verification_result": self.verification_result,
            "outcome": self.outcome.value if self.outcome else "",
        }

    def _gate_status(self, name: str) -> str:
        for g in self.gate_results:
            if g.name == name:
                return g.status.value
        return GateStatus.SKIPPED.value


@dataclass
class PipelineMetrics:
    started_at: str = ""
    ended_at: str = ""
    total_duration_s: float = 0.0
    total_iterations: int = 0
    converged: bool = False
    iterations: list[IterationMetrics] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_duration_s": self.total_duration_s,
            "total_iterations": self.total_iterations,
            "converged": self.converged,
            "iterations": [it.to_dict() for it in self.iterations],
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

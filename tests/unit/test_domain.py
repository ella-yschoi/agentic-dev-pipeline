"""Tests for domain types: enums, GateResult, IterationMetrics, PipelineMetrics."""

import json

from agentic_dev_pipeline.domain import (
    TRIANGULAR_PASS_MARKER,
    GateResult,
    GateStatus,
    IterationMetrics,
    IterationOutcome,
    PipelineMetrics,
)


class TestGateStatus:
    def test_values(self):
        assert GateStatus.PASS.value == "pass"
        assert GateStatus.FAIL.value == "fail"
        assert GateStatus.SKIPPED.value == "skipped"
        assert GateStatus.BLOCKED.value == "blocked"

    def test_from_value(self):
        assert GateStatus("pass") is GateStatus.PASS


class TestIterationOutcome:
    def test_values(self):
        assert IterationOutcome.PASS.value == "pass"
        assert IterationOutcome.GATE_FAIL.value == "gate_fail"
        assert IterationOutcome.VERIFY_FAIL.value == "verify_fail"


class TestTriangularPassMarker:
    def test_value(self):
        assert TRIANGULAR_PASS_MARKER == "TRIANGULAR_PASS"


class TestGateResult:
    def test_defaults(self):
        g = GateResult()
        assert g.name == ""
        assert g.status is GateStatus.SKIPPED
        assert g.output == ""
        assert g.duration_s == 0.0


class TestIterationMetrics:
    def test_lint_result_from_gate_results(self):
        m = IterationMetrics(
            gate_results=[
                GateResult(name="lint", status=GateStatus.PASS),
                GateResult(name="test", status=GateStatus.FAIL),
            ]
        )
        assert m.lint_result == "pass"
        assert m.test_result == "fail"
        assert m.security_result == "skipped"

    def test_plugin_results_excludes_builtins(self):
        m = IterationMetrics(
            gate_results=[
                GateResult(name="lint", status=GateStatus.PASS),
                GateResult(name="plugin:custom", status=GateStatus.FAIL, output="err"),
            ]
        )
        plugins = m.plugin_results
        assert len(plugins) == 1
        assert plugins[0]["name"] == "plugin:custom"
        assert plugins[0]["result"] == "fail"

    def test_verification_result(self):
        m = IterationMetrics(verification_status=GateStatus.PASS)
        assert m.verification_result == "pass"

    def test_to_dict_backward_compat(self):
        m = IterationMetrics(
            iteration=1,
            duration_s=5.0,
            phase1_done=True,
            gate_results=[
                GateResult(name="lint", status=GateStatus.PASS),
                GateResult(name="test", status=GateStatus.PASS),
                GateResult(name="security", status=GateStatus.SKIPPED),
            ],
            verification_status=GateStatus.PASS,
            outcome=IterationOutcome.PASS,
        )
        d = m.to_dict()
        assert d["iteration"] == 1
        assert d["lint_result"] == "pass"
        assert d["test_result"] == "pass"
        assert d["security_result"] == "skipped"
        assert d["plugin_results"] == []
        assert d["verification_result"] == "pass"
        assert d["outcome"] == "pass"
        assert d["phase1_done"] is True

    def test_to_dict_empty_outcome(self):
        m = IterationMetrics()
        assert m.to_dict()["outcome"] == ""


class TestPipelineMetrics:
    def test_to_dict(self):
        pm = PipelineMetrics(
            started_at="2026-01-01T00:00:00",
            ended_at="2026-01-01T00:01:00",
            total_duration_s=60.0,
            total_iterations=1,
            converged=True,
            iterations=[
                IterationMetrics(
                    iteration=1,
                    outcome=IterationOutcome.PASS,
                    gate_results=[GateResult(name="lint", status=GateStatus.PASS)],
                    verification_status=GateStatus.PASS,
                ),
            ],
        )
        d = pm.to_dict()
        assert d["converged"] is True
        assert d["total_iterations"] == 1
        assert len(d["iterations"]) == 1
        assert d["iterations"][0]["lint_result"] == "pass"

    def test_save_produces_valid_json(self, tmp_path):
        pm = PipelineMetrics(
            started_at="2026-01-01T00:00:00",
            ended_at="2026-01-01T00:01:00",
            total_duration_s=60.0,
            total_iterations=1,
            converged=True,
        )
        path = tmp_path / "metrics.json"
        pm.save(path)
        data = json.loads(path.read_text())
        assert data["converged"] is True
        assert data["total_iterations"] == 1

    def test_save_creates_parent_dirs(self, tmp_path):
        pm = PipelineMetrics()
        path = tmp_path / "sub" / "dir" / "metrics.json"
        pm.save(path)
        assert path.is_file()

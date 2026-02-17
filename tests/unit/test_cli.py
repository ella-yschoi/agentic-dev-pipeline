"""Tests for CLI argument parsing."""

import argparse

import pytest

from agentic_dev_pipeline.cli import _build_parser, _positive_int


class TestPositiveInt:
    def test_valid(self):
        assert _positive_int("5") == 5
        assert _positive_int("1") == 1

    def test_zero_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _positive_int("0")

    def test_negative_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _positive_int("-1")

    def test_non_number_raises(self):
        with pytest.raises(ValueError):
            _positive_int("abc")


class TestBuildParser:
    def test_version(self, capsys):
        parser = _build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "agentic-dev-pipeline" in captured.out

    def test_run_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["run", "--prompt", "p.md", "--requirements", "r.md"])
        assert args.command == "run"
        assert args.prompt == "p.md"
        assert args.requirements == "r.md"

    def test_verify_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["verify", "--requirements", "r.md"])
        assert args.command == "verify"
        assert args.requirements == "r.md"

    def test_detect_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["detect"])
        assert args.command == "detect"

    def test_init_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["init"])
        assert args.command == "init"
        assert args.force is False

    def test_init_with_force(self):
        parser = _build_parser()
        args = parser.parse_args(["init", "--force"])
        assert args.command == "init"
        assert args.force is True

    def test_run_with_all_options(self):
        parser = _build_parser()
        args = parser.parse_args([
            "run",
            "--prompt", "p.md",
            "--requirements", "r.md",
            "--output-dir", "out/",
            "--max-iterations", "3",
            "--timeout", "600",
            "--max-retries", "4",
            "--base-branch", "develop",
            "--webhook-url", "https://hooks.example.com/test",
        ])
        assert args.max_iterations == 3
        assert args.timeout == 600
        assert args.max_retries == 4
        assert args.base_branch == "develop"
        assert args.webhook_url == "https://hooks.example.com/test"

    def test_no_command_shows_help(self, capsys):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_run_without_flags_defaults_none(self):
        """CLI flags default to None so config resolution can apply."""
        parser = _build_parser()
        args = parser.parse_args(["run"])
        assert args.prompt is None
        assert args.requirements is None
        assert args.output_dir is None
        assert args.max_iterations is None
        assert args.timeout is None

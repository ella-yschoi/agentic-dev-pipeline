"""Tests for the Logger."""

import json

from agentic_dev_pipeline.log import Logger


class TestLogger:
    def test_text_mode(self, tmp_path, capsys):
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file, json_mode=False)
        logger.info("hello world")

        captured = capsys.readouterr()
        assert "hello world" in captured.out

        content = log_file.read_text()
        assert "hello world" in content

    def test_json_mode(self, tmp_path, capsys):
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file, json_mode=True)
        logger.info("hello json")

        captured = capsys.readouterr()
        record = json.loads(captured.out.strip())
        assert record["msg"] == "hello json"
        assert record["level"] == "info"
        assert "ts" in record
        assert "elapsed_s" in record

    def test_warn_to_stderr(self, tmp_path, capsys):
        logger = Logger(json_mode=False)
        logger.warn("warning!")

        captured = capsys.readouterr()
        assert "warning!" in captured.err
        assert captured.out == ""

    def test_phase_events(self, tmp_path, capsys):
        logger = Logger(json_mode=True)
        logger.phase_start("test_phase", iteration=1)
        logger.phase_end("test_phase", "pass", iteration=1)

        lines = capsys.readouterr().out.strip().splitlines()
        start = json.loads(lines[0])
        end = json.loads(lines[1])
        assert start["event"] == "phase_start"
        assert end["event"] == "phase_end"
        assert end["result"] == "pass"

    def test_no_log_file(self, capsys):
        logger = Logger(json_mode=False)
        logger.info("no file")
        captured = capsys.readouterr()
        assert "no file" in captured.out

    def test_creates_parent_dirs(self, tmp_path):
        log_file = tmp_path / "deep" / "nested" / "test.log"
        logger = Logger(log_file=log_file)
        logger.info("deep")
        assert log_file.parent.exists()

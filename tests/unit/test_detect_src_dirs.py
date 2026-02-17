"""Tests for detect_src_dirs()."""

from agentic_dev_pipeline.detect import detect_src_dirs


class TestDetectSrcDirs:
    def test_src_dir(self, tmp_path, clean_env):
        (tmp_path / "src").mkdir()
        assert detect_src_dirs(tmp_path) == "src/"

    def test_multiple_dirs(self, tmp_path, clean_env):
        (tmp_path / "src").mkdir()
        (tmp_path / "lib").mkdir()
        result = detect_src_dirs(tmp_path)
        assert "src/" in result
        assert "lib/" in result

    def test_all_dirs(self, tmp_path, clean_env):
        for d in ("src", "app", "lib", "pkg"):
            (tmp_path / d).mkdir()
        result = detect_src_dirs(tmp_path)
        for d in ("src/", "app/", "lib/", "pkg/"):
            assert d in result

    def test_no_dirs_fallback_to_dot(self, tmp_path, clean_env):
        assert detect_src_dirs(tmp_path) == "."

    def test_env_override(self, tmp_path, monkeypatch, clean_env):
        (tmp_path / "src").mkdir()
        monkeypatch.setenv("SRC_DIRS", "custom/")
        assert detect_src_dirs(tmp_path) == "custom/"

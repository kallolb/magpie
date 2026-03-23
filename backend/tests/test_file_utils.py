"""Tests for app.utils.file_utils."""

import pytest
from pathlib import Path

from app.utils.file_utils import safe_filename, get_video_path, ensure_category_dir, get_storage_stats


class TestSafeFilename:
    """Tests for safe_filename()."""

    def test_simple_title(self):
        assert safe_filename("My Video Title") == "My Video Title"

    def test_removes_invalid_chars(self):
        assert safe_filename('Video: "The Best" <One>') == "Video The Best One"

    def test_removes_pipe_and_question(self):
        # pipe is not in the invalid set, question mark is removed, multi-spaces collapsed
        result = safe_filename("What is this? | Explained")
        assert "?" not in result

    def test_removes_backslash_and_forward_slash(self):
        assert safe_filename("path/to\\file") == "pathtofile"

    def test_strips_leading_trailing_dots_and_spaces(self):
        assert safe_filename("...  My Title  ...") == "My Title"

    def test_collapses_multiple_spaces(self):
        assert safe_filename("Too    Many   Spaces") == "Too Many Spaces"

    def test_truncates_to_200_chars(self):
        long_title = "A" * 300
        result = safe_filename(long_title)
        assert len(result) == 200

    def test_unicode_preserved(self):
        result = safe_filename("日本語タイトル ｜ Deep Learning")
        assert "日本語タイトル" in result

    def test_empty_string(self):
        assert safe_filename("") == ""

    def test_only_invalid_chars(self):
        assert safe_filename('<>:"/\\|?*') == ""


class TestGetVideoPath:
    """Tests for get_video_path()."""

    def test_builds_correct_path(self):
        result = get_video_path("/data", "tutorials", "my_video.mp4")
        expected = str(Path("/data") / "categories" / "tutorials" / "my_video.mp4")
        assert result == expected

    def test_nested_storage_root(self):
        result = get_video_path("/mnt/nas/videos", "music", "song.mp4")
        assert "categories/music/song.mp4" in result


class TestEnsureCategoryDir:
    """Tests for ensure_category_dir()."""

    def test_creates_directory(self, tmp_path):
        storage = tmp_path / "storage"
        storage.mkdir()
        result = ensure_category_dir(str(storage), "tutorials")
        assert Path(result).exists()
        assert Path(result).is_dir()

    def test_idempotent(self, tmp_path):
        storage = tmp_path / "storage"
        storage.mkdir()
        result1 = ensure_category_dir(str(storage), "music")
        result2 = ensure_category_dir(str(storage), "music")
        assert result1 == result2

    def test_returns_correct_path(self, tmp_path):
        storage = tmp_path / "storage"
        storage.mkdir()
        result = ensure_category_dir(str(storage), "gaming")
        assert result.endswith("categories/gaming")


class TestGetStorageStats:
    """Tests for get_storage_stats()."""

    def test_returns_all_keys(self, tmp_path):
        stats = get_storage_stats(str(tmp_path))
        assert "total_bytes" in stats
        assert "used_bytes" in stats
        assert "free_bytes" in stats
        assert "local_used_bytes" in stats

    def test_counts_files(self, tmp_path):
        # Create some test files
        (tmp_path / "file1.txt").write_text("hello")
        (tmp_path / "file2.txt").write_text("world!!")
        stats = get_storage_stats(str(tmp_path))
        assert stats["local_used_bytes"] == 5 + 7

    def test_counts_nested_files(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "nested.txt").write_bytes(b"x" * 100)
        stats = get_storage_stats(str(tmp_path))
        assert stats["local_used_bytes"] == 100

    def test_invalid_path_returns_zeros(self):
        stats = get_storage_stats("/nonexistent/path/that/does/not/exist")
        assert stats["local_used_bytes"] == 0

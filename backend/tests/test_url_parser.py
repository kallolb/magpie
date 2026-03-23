"""Tests for app.utils.url_parser."""

import pytest

from app.utils.url_parser import detect_platform, extract_video_id


class TestDetectPlatform:
    """Tests for detect_platform()."""

    def test_youtube_watch_url(self):
        assert detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"

    def test_youtube_short_url(self):
        assert detect_platform("https://youtu.be/dQw4w9WgXcQ") == "youtube"

    def test_youtube_case_insensitive(self):
        assert detect_platform("https://YOUTUBE.COM/watch?v=abc") == "youtube"

    def test_instagram_post(self):
        assert detect_platform("https://www.instagram.com/p/ABC123/") == "instagram"

    def test_instagram_reel(self):
        assert detect_platform("https://www.instagram.com/reel/XYZ789/") == "instagram"

    def test_instagram_short_url(self):
        assert detect_platform("https://instagr.am/p/ABC123/") == "instagram"

    def test_tiktok_video(self):
        assert detect_platform("https://www.tiktok.com/@user/video/123456789") == "tiktok"

    def test_tiktok_short_url(self):
        assert detect_platform("https://vm.tiktok.com/ZM123/") == "tiktok"

    def test_twitter_status(self):
        assert detect_platform("https://twitter.com/user/status/123456") == "twitter"

    def test_x_status(self):
        assert detect_platform("https://x.com/user/status/123456") == "twitter"

    def test_t_co_short_url(self):
        assert detect_platform("https://t.co/abc123") == "twitter"

    def test_unknown_url(self):
        assert detect_platform("https://example.com/video.mp4") == "other"

    def test_empty_url(self):
        assert detect_platform("") == "other"


class TestExtractVideoId:
    """Tests for extract_video_id()."""

    def test_youtube_watch_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url, "youtube") == "dQw4w9WgXcQ"

    def test_youtube_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url, "youtube") == "dQw4w9WgXcQ"

    def test_youtube_with_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42"
        assert extract_video_id(url, "youtube") == "dQw4w9WgXcQ"

    def test_youtube_no_match(self):
        url = "https://www.youtube.com/channel/UC123"
        assert extract_video_id(url, "youtube") is None

    def test_instagram_post(self):
        url = "https://www.instagram.com/p/ABC123xyz/"
        assert extract_video_id(url, "instagram") == "ABC123xyz"

    def test_instagram_reel(self):
        url = "https://www.instagram.com/reel/DVbxqV4DDd0/"
        assert extract_video_id(url, "instagram") == "DVbxqV4DDd0"

    def test_instagram_reel_with_params(self):
        url = "https://www.instagram.com/reel/DVbxqV4DDd0/?utm_source=ig_web_copy_link"
        assert extract_video_id(url, "instagram") == "DVbxqV4DDd0"

    def test_instagram_stories(self):
        url = "https://www.instagram.com/stories/user123/456789/"
        assert extract_video_id(url, "instagram") == "user123"

    def test_tiktok_video_url(self):
        url = "https://www.tiktok.com/@user/video/7123456789012345678"
        assert extract_video_id(url, "tiktok") == "7123456789012345678"

    def test_tiktok_vm_url(self):
        url = "https://vm.tiktok.com/7123456789/"
        assert extract_video_id(url, "tiktok") == "7123456789"

    def test_twitter_status(self):
        url = "https://twitter.com/user/status/1234567890123456"
        assert extract_video_id(url, "twitter") == "1234567890123456"

    def test_x_status(self):
        url = "https://x.com/elonmusk/status/9876543210"
        assert extract_video_id(url, "twitter") == "9876543210"

    def test_other_platform_returns_last_segment(self):
        url = "https://example.com/videos/my-video"
        assert extract_video_id(url, "other") == "my-video"

    def test_other_platform_trailing_slash(self):
        url = "https://example.com/videos/my-video/"
        assert extract_video_id(url, "other") == "my-video"

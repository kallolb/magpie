"""Tests for app.services.categorizer."""

import pytest

from app.services.categorizer import auto_categorize


class TestAutoCategorizePlatformShortForm:
    """Short-form detection by platform."""

    def test_instagram_always_short_form(self):
        assert auto_categorize("Random video", None, "instagram", 300) == "short-form"

    def test_tiktok_always_short_form(self):
        assert auto_categorize("Random video", None, "tiktok", 600) == "short-form"

    def test_short_duration_any_platform(self):
        assert auto_categorize("Random video", None, "youtube", 45) == "short-form"

    def test_exactly_60_seconds_not_short_form(self):
        # duration < 60 triggers short-form, so 60 should NOT trigger it
        result = auto_categorize("Random video", None, "youtube", 60)
        assert result != "short-form"


class TestAutoCategorizeTutorials:
    """Tutorial category detection."""

    def test_tutorial_in_title(self):
        assert auto_categorize("Python Tutorial", None, "youtube", 1800) == "tutorials"

    def test_how_to_in_title(self):
        assert auto_categorize("How to Build a Web App", None, "youtube", 600) == "tutorials"

    def test_learn_in_description(self):
        assert auto_categorize("Video", "Learn Python today", "youtube", 600) == "tutorials"

    def test_guide_in_title(self):
        assert auto_categorize("Complete Guide to Docker", None, "youtube", 3600) == "tutorials"

    def test_course_in_title(self):
        assert auto_categorize("Full Course on React", None, "youtube", 7200) == "tutorials"


class TestAutoCategorizeMusic:
    """Music category detection."""

    def test_music_in_title(self):
        assert auto_categorize("Background Music Mix", None, "youtube", 3600) == "music"

    def test_song_in_title(self):
        assert auto_categorize("New Song 2024", None, "youtube", 240) == "music"

    def test_remix_in_title(self):
        assert auto_categorize("Epic Remix", None, "youtube", 300) == "music"

    def test_cover_in_description(self):
        assert auto_categorize("Performance", "Guitar cover of classic", "youtube", 300) == "music"


class TestAutoCategorizeCooking:
    """Cooking category detection."""

    def test_recipe_in_title(self):
        assert auto_categorize("Easy Pasta Recipe", None, "youtube", 600) == "cooking"

    def test_cooking_in_title(self):
        assert auto_categorize("Cooking with Mom", None, "youtube", 900) == "cooking"

    def test_chef_in_description(self):
        assert auto_categorize("Pro Tips", "Chef shows technique", "youtube", 600) == "cooking"


class TestAutoCategorizeGaming:
    """Gaming category detection."""

    def test_gameplay_in_title(self):
        assert auto_categorize("GTA V Gameplay", None, "youtube", 1200) == "gaming"

    def test_lets_play_in_title(self):
        # "game" keyword in the title should match gaming
        assert auto_categorize("Let's Play This Game", None, "youtube", 1800) == "gaming"

    def test_walkthrough_in_title(self):
        assert auto_categorize("Full Walkthrough", None, "youtube", 7200) == "gaming"


class TestAutoCategorizeTech:
    """Tech category detection."""

    def test_programming_in_title(self):
        assert auto_categorize("Programming in Rust", None, "youtube", 600) == "tech"

    def test_code_in_title(self):
        assert auto_categorize("Code Review Session", None, "youtube", 900) == "tech"

    def test_software_in_description(self):
        assert auto_categorize("Review", "Best software tools 2024", "youtube", 600) == "tech"

    def test_api_in_title(self):
        assert auto_categorize("Building a REST API", None, "youtube", 1200) == "tech"


class TestAutoCategorizeSports:
    """Sports category detection."""

    def test_football_in_title(self):
        assert auto_categorize("Football Highlights", None, "youtube", 600) == "sports"

    def test_basketball_in_title(self):
        assert auto_categorize("NBA Basketball Best Plays", None, "youtube", 900) == "sports"

    def test_championship_in_description(self):
        assert auto_categorize("Final", "World Championship 2024", "youtube", 3600) == "sports"


class TestAutoCategorizeNews:
    """News category detection."""

    def test_news_in_title(self):
        assert auto_categorize("Morning News", None, "youtube", 1800) == "news"

    def test_breaking_in_title(self):
        assert auto_categorize("Breaking: Major Event", None, "youtube", 300) == "news"

    def test_report_in_description(self):
        assert auto_categorize("Update", "Full report on events", "youtube", 600) == "news"


class TestAutoCategorizeEntertainment:
    """Entertainment category detection."""

    def test_funny_in_title(self):
        assert auto_categorize("Funny Moments", None, "youtube", 600) == "entertainment"

    def test_comedy_in_title(self):
        assert auto_categorize("Stand-up Comedy Special", None, "youtube", 3600) == "entertainment"

    def test_vlog_in_title(self):
        assert auto_categorize("Daily Vlog #42", None, "youtube", 900) == "entertainment"


class TestAutoCategorizeUncategorized:
    """Fallback to uncategorized."""

    def test_no_matching_keywords(self):
        assert auto_categorize("Random Title Here", None, "youtube", 600) == "uncategorized"

    def test_empty_title(self):
        assert auto_categorize("", None, "youtube", 600) == "uncategorized"

    def test_none_description(self):
        result = auto_categorize("Something", None, "youtube", 600)
        # Should not raise, description=None is handled
        assert isinstance(result, str)


class TestAutoCategorizePriority:
    """Verify short-form takes priority over keyword matching."""

    def test_instagram_tutorial_still_short_form(self):
        # Instagram should always be short-form, even if title says "tutorial"
        assert auto_categorize("Python Tutorial", None, "instagram", 1800) == "short-form"

    def test_short_duration_tutorial_still_short_form(self):
        assert auto_categorize("Quick Tutorial", None, "youtube", 30) == "short-form"

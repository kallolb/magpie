"""Tests for app.models (Pydantic schemas)."""

import pytest
from pydantic import ValidationError

from app.models.video import (
    VideoCreate,
    VideoUpdate,
    VideoResponse,
    VideoListResponse,
    DownloadRequest,
    DownloadStatus,
    SearchRequest,
)
from app.models.tag import TagCreate, TagResponse
from app.models.category import CategoryCreate, CategoryResponse


class TestVideoUpdate:
    """Tests for VideoUpdate model."""

    def test_all_none_valid(self):
        update = VideoUpdate()
        assert update.title is None
        assert update.category is None
        assert update.tags is None

    def test_partial_update(self):
        update = VideoUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.category is None

    def test_tags_as_list(self):
        update = VideoUpdate(tags=["tag1", "tag2"])
        assert update.tags == ["tag1", "tag2"]

    def test_empty_tags_list(self):
        update = VideoUpdate(tags=[])
        assert update.tags == []

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            VideoUpdate(title="test", nonexistent_field="value")


class TestVideoResponse:
    """Tests for VideoResponse model."""

    def _make_video_data(self, **overrides):
        base = {
            "id": "test-id",
            "source_url": "https://youtube.com/watch?v=abc",
            "platform": "youtube",
            "platform_id": "abc",
            "title": "Test Video",
            "description": None,
            "uploader": None,
            "upload_date": None,
            "duration_secs": 120,
            "resolution": "1080p",
            "file_path": "categories/tech/test.mp4",
            "file_size_bytes": 1000000,
            "thumbnail_path": None,
            "category": "tech",
            "status": "completed",
            "error_message": None,
            "progress": 100.0,
            "created_at": "2024-01-01 00:00:00",
            "updated_at": "2024-01-01 00:00:00",
            "tags": [],
        }
        base.update(overrides)
        return base

    def test_basic_response(self):
        data = self._make_video_data()
        resp = VideoResponse(**data)
        assert resp.id == "test-id"
        assert resp.title == "Test Video"

    def test_thumbnail_path_prefixed(self):
        data = self._make_video_data(thumbnail_path="thumbnails/test-id.jpg")
        resp = VideoResponse(**data)
        assert resp.thumbnail_path == "/api/thumbnails/test-id.jpg"

    def test_thumbnail_path_none_stays_none(self):
        data = self._make_video_data(thumbnail_path=None)
        resp = VideoResponse(**data)
        assert resp.thumbnail_path is None

    def test_thumbnail_path_already_prefixed(self):
        data = self._make_video_data(thumbnail_path="/api/thumbnails/test-id.jpg")
        resp = VideoResponse(**data)
        assert resp.thumbnail_path == "/api/thumbnails/test-id.jpg"

    def test_tags_list(self):
        data = self._make_video_data(tags=["python", "tutorial"])
        resp = VideoResponse(**data)
        assert resp.tags == ["python", "tutorial"]

    def test_duration_none_allowed(self):
        data = self._make_video_data(duration_secs=None)
        resp = VideoResponse(**data)
        assert resp.duration_secs is None

    def test_duration_must_be_int(self):
        data = self._make_video_data(duration_secs=6.5)
        with pytest.raises(ValidationError):
            VideoResponse(**data)


class TestDownloadRequest:
    """Tests for DownloadRequest model."""

    def test_minimal_request(self):
        req = DownloadRequest(url="https://youtube.com/watch?v=abc")
        assert req.url == "https://youtube.com/watch?v=abc"
        assert req.quality == 1080  # default

    def test_full_request(self):
        req = DownloadRequest(
            url="https://youtube.com/watch?v=abc",
            category="tutorials",
            tags=["python", "beginner"],
            quality=720,
        )
        assert req.category == "tutorials"
        assert req.tags == ["python", "beginner"]
        assert req.quality == 720

    def test_url_required(self):
        with pytest.raises(ValidationError):
            DownloadRequest()


class TestSearchRequest:
    """Tests for SearchRequest model."""

    def test_minimal_search(self):
        req = SearchRequest(query="python tutorial")
        assert req.query == "python tutorial"
        assert req.page == 1
        assert req.per_page == 20

    def test_with_filters(self):
        req = SearchRequest(
            query="python", category="tutorials", tags=["beginner"], page=2, per_page=10
        )
        assert req.category == "tutorials"
        assert req.tags == ["beginner"]
        assert req.page == 2

    def test_per_page_max_100(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", per_page=101)

    def test_page_min_1(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", page=0)


class TestTagModels:
    """Tests for Tag models."""

    def test_tag_create(self):
        tag = TagCreate(name="python")
        assert tag.name == "python"

    def test_tag_response(self):
        tag = TagResponse(id=1, name="python", video_count=5)
        assert tag.id == 1
        assert tag.video_count == 5


class TestCategoryModels:
    """Tests for Category models."""

    def test_category_create_minimal(self):
        cat = CategoryCreate(name="tutorials")
        assert cat.name == "tutorials"

    def test_category_create_with_description(self):
        cat = CategoryCreate(name="tutorials", description="How-to videos")
        assert cat.description == "How-to videos"

    def test_category_response(self):
        cat = CategoryResponse(
            name="tutorials", description="How-to videos", video_count=10, created_at="2024-01-01"
        )
        assert cat.video_count == 10

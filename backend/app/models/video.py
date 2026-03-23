from typing import Optional

from pydantic import BaseModel, Field, model_validator


class VideoCreate(BaseModel):
    """Request model for creating a video download."""

    source_url: str = Field(..., description="URL of the video to download")
    category: Optional[str] = Field(
        default=None, description="Category to place the video in"
    )
    tags: Optional[list[str]] = Field(
        default=None, description="Tags to apply to the video"
    )


class VideoUpdate(BaseModel):
    """Request model for updating a video."""

    title: Optional[str] = Field(default=None, description="Video title")
    category: Optional[str] = Field(default=None, description="Category")
    tags: Optional[list[str]] = Field(default=None, description="Tags")

    class Config:
        extra = "forbid"


class VideoResponse(BaseModel):
    """Response model for a video."""

    id: str
    source_url: str
    platform: str
    platform_id: Optional[str]
    title: str
    description: Optional[str]
    uploader: Optional[str]
    upload_date: Optional[str]
    duration_secs: Optional[int]
    resolution: Optional[str]
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    thumbnail_path: Optional[str]
    category: str
    status: str
    error_message: Optional[str]
    progress: float
    created_at: str
    updated_at: str
    tags: list[str]

    @model_validator(mode="before")
    @classmethod
    def prefix_thumbnail_path(cls, data: dict) -> dict:
        """Prefix thumbnail_path with /api/ so it resolves through the proxy."""
        if isinstance(data, dict):
            tp = data.get("thumbnail_path")
            if tp and not tp.startswith("/"):
                data["thumbnail_path"] = f"/api/{tp}"
        return data

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """Paginated list of videos."""

    items: list[VideoResponse]
    total: int
    page: int
    per_page: int


class DownloadRequest(BaseModel):
    """Request model for starting a download."""

    url: str = Field(..., description="URL of the video")
    category: Optional[str] = Field(
        default=None, description="Category for the video"
    )
    tags: Optional[list[str]] = Field(default=None, description="Tags for the video")
    quality: Optional[int] = Field(
        default=1080, description="Preferred video quality in pixels"
    )


class DownloadStatus(BaseModel):
    """Status of a video download."""

    id: str
    status: str
    progress: float
    error_message: Optional[str]
    video: Optional[VideoResponse] = None


class SearchRequest(BaseModel):
    """Request model for searching videos."""

    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(
        default=None, description="Filter by category"
    )
    tags: Optional[list[str]] = Field(
        default=None, description="Filter by tags"
    )
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

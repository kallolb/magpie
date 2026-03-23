from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """Request model for creating a category."""

    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(
        default=None, description="Category description"
    )

    class Config:
        extra = "forbid"


class CategoryResponse(BaseModel):
    """Response model for a category."""

    name: str
    description: Optional[str]
    video_count: int
    created_at: str

    class Config:
        from_attributes = True

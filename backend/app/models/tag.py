from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    """Request model for creating a tag."""

    name: str = Field(..., description="Tag name")

    class Config:
        extra = "forbid"


class TagResponse(BaseModel):
    """Response model for a tag."""

    id: int
    name: str
    video_count: int

    class Config:
        from_attributes = True

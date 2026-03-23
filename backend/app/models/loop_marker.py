from typing import Optional

from pydantic import BaseModel, Field


class LoopMarkerCreate(BaseModel):
    """Request model for creating a loop marker."""

    label: str = Field(..., description="Label for the loop (e.g. 'Chorus', 'Guitar solo')")
    start_secs: float = Field(..., ge=0, description="Start time in seconds")
    end_secs: float = Field(..., ge=0, description="End time in seconds")


class LoopMarkerResponse(BaseModel):
    """Response model for a loop marker."""

    id: int
    video_id: str
    label: str
    start_secs: float
    end_secs: float
    created_at: str

    class Config:
        from_attributes = True

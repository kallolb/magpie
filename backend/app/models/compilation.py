from typing import Optional

from pydantic import BaseModel, Field


class CompilationCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    category: str = Field(default="compilations")


class CompilationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    category: Optional[str] = None


class ClipCreate(BaseModel):
    source_video_id: str
    start_secs: float = Field(..., ge=0)
    end_secs: float = Field(..., ge=0)
    label: Optional[str] = None


class ClipUpdate(BaseModel):
    start_secs: Optional[float] = Field(default=None, ge=0)
    end_secs: Optional[float] = Field(default=None, ge=0)
    label: Optional[str] = None


class ClipReorder(BaseModel):
    clip_ids: list[int] = Field(..., min_length=1)


class ClipResponse(BaseModel):
    id: int
    compilation_id: str
    source_video_id: str
    source_video_title: Optional[str] = None
    source_video_thumbnail: Optional[str] = None
    position: int
    start_secs: float
    end_secs: float
    duration_secs: float = 0
    label: Optional[str] = None
    created_at: str


class CompilationResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    status: str
    render_mode: Optional[str] = None
    output_path: Optional[str] = None
    output_size_bytes: Optional[int] = None
    duration_secs: Optional[float] = None
    thumbnail_path: Optional[str] = None
    error_message: Optional[str] = None
    clip_count: int = 0
    estimated_duration_secs: float = 0
    created_at: str
    updated_at: str
    clips: list[ClipResponse] = []

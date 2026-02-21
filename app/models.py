from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class CaptureRequest(BaseModel):
    artist: str = Field(min_length=1)
    title: str = Field(min_length=1)
    show_date: str | None = Field(default=None, description="YYYY-MM-DD preferred")


class CaptureResponse(BaseModel):
    request_id: int
    status: str
    created_at: datetime

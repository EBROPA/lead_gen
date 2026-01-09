"""Pydantic schemas for Source model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.source import SourceType


class SourceBase(BaseModel):
    """Base schema for Source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = SourceType.OTHER
    url: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    is_active: bool = True
    search_keywords: Optional[list[str]] = None
    parser_config: Optional[dict] = None


class SourceCreate(SourceBase):
    """Schema for creating a new Source."""
    pass


class SourceUpdate(BaseModel):
    """Schema for updating a Source."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    source_type: Optional[SourceType] = None
    url: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    search_keywords: Optional[list[str]] = None
    parser_config: Optional[dict] = None


class SourceResponse(SourceBase):
    """Schema for Source response."""
    id: int
    total_leads_found: int
    qualified_leads_count: int
    last_search_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    conversion_rate: float

    class Config:
        from_attributes = True


class SourceStats(BaseModel):
    """Statistics for a source."""
    source_id: int
    source_name: str
    total_leads: int
    qualified_leads: int
    conversion_rate: float
    hot_leads: int

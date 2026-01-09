"""Pydantic schemas for Lead model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from app.models.lead import LeadStatus


class LeadBase(BaseModel):
    """Base schema for Lead."""
    name: str = Field(..., min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    telegram: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=500)
    social_links: Optional[dict] = None
    business_description: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    business_size: Optional[str] = Field(None, max_length=50)
    original_request: Optional[str] = None
    needs_description: Optional[str] = None
    budget_mentioned: Optional[str] = Field(None, max_length=100)
    urgency: Optional[str] = Field(None, max_length=50)


class LeadCreate(LeadBase):
    """Schema for creating a new Lead."""
    source_id: Optional[int] = None
    source_url: Optional[str] = Field(None, max_length=1000)


class LeadUpdate(BaseModel):
    """Schema for updating a Lead."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    telegram: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=500)
    social_links: Optional[dict] = None
    business_description: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    business_size: Optional[str] = Field(None, max_length=50)
    needs_description: Optional[str] = None
    budget_mentioned: Optional[str] = Field(None, max_length=100)
    urgency: Optional[str] = Field(None, max_length=50)
    status: Optional[LeadStatus] = None
    priority: Optional[int] = None
    qualification_notes: Optional[str] = None


class WebsiteAnalysisResponse(BaseModel):
    """Schema for website analysis in lead response."""
    url: str
    is_accessible: bool
    overall_score: Optional[float] = None
    performance_score: Optional[float] = None
    issues: Optional[list] = None
    improvement_suggestions: Optional[list] = None
    analyzed_at: datetime

    class Config:
        from_attributes = True


class LeadResponse(LeadBase):
    """Schema for Lead response."""
    id: int
    source_id: Optional[int] = None
    source_url: Optional[str] = None
    found_at: datetime
    qualification_score: Optional[float] = None
    budget_score: Optional[float] = None
    urgency_score: Optional[float] = None
    fit_score: Optional[float] = None
    status: LeadStatus
    priority: int
    ai_analysis: Optional[dict] = None
    qualification_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    website_analysis: Optional[WebsiteAnalysisResponse] = None

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Schema for paginated lead list response."""
    items: list[LeadResponse]
    total: int
    page: int
    per_page: int
    pages: int


class LeadSearchFilters(BaseModel):
    """Schema for lead search/filter parameters."""
    status: Optional[LeadStatus] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    max_score: Optional[float] = Field(None, ge=0, le=100)
    industry: Optional[str] = None
    source_id: Optional[int] = None
    has_website: Optional[bool] = None
    has_contact: Optional[bool] = None
    search_query: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

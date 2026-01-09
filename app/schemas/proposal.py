"""Pydantic schemas for Proposal model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.proposal import ProposalStatus, ProposalChannel


class ProposalBase(BaseModel):
    """Base schema for Proposal."""
    subject: Optional[str] = Field(None, max_length=500)
    content: str
    channel: ProposalChannel = ProposalChannel.EMAIL


class ProposalCreate(ProposalBase):
    """Schema for creating a new Proposal."""
    lead_id: int
    personalization_data: Optional[dict] = None
    website_issues: Optional[list] = None
    suggested_solutions: Optional[list] = None
    portfolio_examples: Optional[list] = None


class ProposalUpdate(BaseModel):
    """Schema for updating a Proposal."""
    subject: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    status: Optional[ProposalStatus] = None


class ProposalResponse(ProposalBase):
    """Schema for Proposal response."""
    id: int
    lead_id: int
    status: ProposalStatus
    version: int
    personalization_data: Optional[dict] = None
    website_issues: Optional[list] = None
    suggested_solutions: Optional[list] = None
    portfolio_examples: Optional[list] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProposalGenerateRequest(BaseModel):
    """Request schema for generating a proposal."""
    lead_id: int
    channel: ProposalChannel = ProposalChannel.EMAIL
    tone: str = Field(default="professional", description="Tone: professional, friendly, casual")
    include_portfolio: bool = True
    include_website_analysis: bool = True
    custom_notes: Optional[str] = None


class ProposalGenerateResponse(BaseModel):
    """Response schema for generated proposal."""
    proposal_id: int
    lead_id: int
    subject: Optional[str] = None
    content: str
    channel: ProposalChannel
    personalization_highlights: list[str]
    website_issues_mentioned: list[str]
    suggested_call_to_action: str

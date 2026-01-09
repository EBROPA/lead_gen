"""Lead model for storing potential clients."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LeadStatus(str, enum.Enum):
    """Status of a lead in the pipeline."""
    NEW = "new"                      # Newly discovered
    QUALIFYING = "qualifying"         # Being qualified
    QUALIFIED = "qualified"           # Qualified and ready for outreach
    CONTACTED = "contacted"           # Initial contact made
    RESPONDED = "responded"           # Lead responded
    NEGOTIATING = "negotiating"       # In negotiation
    WON = "won"                       # Converted to client
    LOST = "lost"                     # Did not convert
    DISQUALIFIED = "disqualified"     # Not a fit
    SPAM = "spam"                     # Spam/fake


class Lead(Base):
    """Model representing a potential client (lead)."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Contact Information
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    telegram: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    social_links: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Business Information
    business_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # small, medium, large

    # Lead Details
    original_request: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Original message/post
    needs_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # What they need
    budget_mentioned: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # low, medium, high, urgent

    # Source Information
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    found_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Qualification Scores (0-100)
    qualification_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    urgency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fit_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status & Pipeline
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus),
        default=LeadStatus.NEW,
        nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Higher = more important

    # AI Analysis
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    qualification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    source: Mapped[Optional["Source"]] = relationship("Source", back_populates="leads")
    proposals: Mapped[list["Proposal"]] = relationship("Proposal", back_populates="lead")
    website_analysis: Mapped[Optional["WebsiteAnalysis"]] = relationship(
        "WebsiteAnalysis",
        back_populates="lead",
        uselist=False
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, name='{self.name}', status={self.status.value})>"

    @property
    def is_hot(self) -> bool:
        """Check if lead is considered 'hot' (high priority)."""
        return (
            self.qualification_score is not None
            and self.qualification_score >= 70
            and self.status in [LeadStatus.NEW, LeadStatus.QUALIFIED]
        )

    @property
    def contact_available(self) -> bool:
        """Check if any contact method is available."""
        return any([self.email, self.phone, self.telegram])


# Import at end to avoid circular imports
from app.models.source import Source
from app.models.proposal import Proposal
from app.models.website_analysis import WebsiteAnalysis

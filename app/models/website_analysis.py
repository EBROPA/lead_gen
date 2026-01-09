"""Website analysis model for storing analysis results."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.lead import Lead


class WebsiteAnalysis(Base):
    """Model for storing website analysis results."""

    __tablename__ = "website_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Lead Reference
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Basic Analysis
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    load_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Technical Analysis
    has_ssl: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_mobile_friendly: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_responsive_design: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Performance Scores (0-100)
    performance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    seo_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accessibility_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    design_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Content Analysis
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_contact_form: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_social_links: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Technology Detection
    technologies: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    cms_detected: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Issues Found
    issues: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    improvement_suggestions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Raw Data
    raw_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="website_analysis")

    def __repr__(self) -> str:
        return f"<WebsiteAnalysis(id={self.id}, url='{self.url}', score={self.overall_score})>"

    @property
    def needs_improvement(self) -> bool:
        """Check if website needs significant improvement."""
        return (
            self.overall_score is not None
            and self.overall_score < 60
        )

    @property
    def critical_issues_count(self) -> int:
        """Count critical issues."""
        if not self.issues:
            return 0
        return sum(1 for issue in self.issues if issue.get("severity") == "critical")

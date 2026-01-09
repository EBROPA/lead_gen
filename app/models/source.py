"""Source model for tracking where leads come from."""

import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, Boolean, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.lead import Lead


class SourceType(str, enum.Enum):
    """Types of lead sources."""
    TELEGRAM_CHANNEL = "telegram_channel"
    TELEGRAM_CHAT = "telegram_chat"
    FORUM = "forum"
    FREELANCE_PLATFORM = "freelance_platform"
    SOCIAL_MEDIA = "social_media"
    JOB_BOARD = "job_board"
    CLASSIFIED_ADS = "classified_ads"
    DIRECTORY = "directory"
    MANUAL = "manual"
    OTHER = "other"


class Source(Base):
    """Model representing a source for finding leads."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType),
        default=SourceType.OTHER,
        nullable=False
    )
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    search_keywords: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    parser_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Statistics
    total_leads_found: Mapped[int] = mapped_column(Integer, default=0)
    qualified_leads_count: Mapped[int] = mapped_column(Integer, default=0)
    last_search_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="source")

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name='{self.name}', type={self.source_type.value})>"

    @property
    def conversion_rate(self) -> float:
        """Calculate lead qualification rate."""
        if self.total_leads_found == 0:
            return 0.0
        return (self.qualified_leads_count / self.total_leads_found) * 100

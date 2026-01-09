"""Proposal model for storing generated proposals for leads."""

import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.lead import Lead


class ProposalStatus(str, enum.Enum):
    """Status of a proposal."""
    DRAFT = "draft"
    READY = "ready"
    SENT = "sent"
    OPENED = "opened"
    REPLIED = "replied"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ProposalChannel(str, enum.Enum):
    """Communication channel for proposal."""
    EMAIL = "email"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"


class Proposal(Base):
    """Model representing a proposal/outreach message for a lead."""

    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Lead Reference
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)

    # Proposal Content
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[ProposalChannel] = mapped_column(
        Enum(ProposalChannel),
        default=ProposalChannel.EMAIL,
        nullable=False
    )

    # Personalization Data
    personalization_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    website_issues: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    suggested_solutions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    portfolio_examples: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus),
        default=ProposalStatus.DRAFT,
        nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="proposals")

    def __repr__(self) -> str:
        return f"<Proposal(id={self.id}, lead_id={self.lead_id}, status={self.status.value})>"

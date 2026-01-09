"""Tests for lead qualification service."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead, LeadStatus
from app.services.lead_qualifier import LeadQualifierService


class TestLeadQualifierService:
    """Tests for LeadQualifierService."""

    def test_detect_industry(self, db_session: AsyncSession):
        """Test industry detection."""
        qualifier = LeadQualifierService(db_session)

        assert qualifier.detect_industry("интернет-магазин одежды") == "e-commerce"
        assert qualifier.detect_industry("ресторан итальянской кухни") == "restaurant"
        assert qualifier.detect_industry("юридические услуги") == "services"
        assert qualifier.detect_industry("фитнес-клуб") == "fitness"
        assert qualifier.detect_industry("random text") is None

    def test_estimate_budget_level(self, db_session: AsyncSession):
        """Test budget level estimation."""
        qualifier = LeadQualifierService(db_session)

        # High budget
        level, score = qualifier.estimate_budget_level("бюджет 200 тыс рублей")
        assert level == "high"
        assert score > 70

        # Medium budget
        level, score = qualifier.estimate_budget_level("бюджет 50 тыс")
        assert level == "medium"
        assert 50 <= score <= 70

        # Low budget
        level, score = qualifier.estimate_budget_level("бюджет 10 тыс")
        assert level == "low"
        assert score < 50

        # Unknown budget
        level, score = qualifier.estimate_budget_level("нужен сайт")
        assert level == "unknown"
        assert score == 50

    def test_estimate_urgency_level(self, db_session: AsyncSession):
        """Test urgency level estimation."""
        qualifier = LeadQualifierService(db_session)

        # Urgent
        level, score = qualifier.estimate_urgency_level("срочно нужен сайт")
        assert level == "urgent"
        assert score > 90

        # High urgency
        level, score = qualifier.estimate_urgency_level("нужно быстро сделать")
        assert level == "high"
        assert 70 <= score <= 90

        # Normal urgency
        level, score = qualifier.estimate_urgency_level("нужен сайт")
        assert level == "normal"
        assert score < 50

    def test_check_disqualification(self, db_session: AsyncSession):
        """Test disqualification checks."""
        qualifier = LeadQualifierService(db_session)

        # Should disqualify
        should_disqualify, reason = qualifier.check_disqualification("нужен сайт бесплатно")
        assert should_disqualify is True

        should_disqualify, reason = qualifier.check_disqualification("сайт для казино")
        assert should_disqualify is True

        # Should not disqualify
        should_disqualify, reason = qualifier.check_disqualification("нужен сайт для магазина")
        assert should_disqualify is False

    def test_calculate_fit_score(self, db_session: AsyncSession):
        """Test fit score calculation."""
        qualifier = LeadQualifierService(db_session)

        # Good fit
        score = qualifier.calculate_fit_score(
            has_contact=True,
            has_website=True,
            website_score=40,  # Poor website
            budget_level="high",
            urgency_level="urgent",
            industry="e-commerce",
        )
        assert score > 80

        # Poor fit
        score = qualifier.calculate_fit_score(
            has_contact=False,
            has_website=False,
            website_score=None,
            budget_level="low",
            urgency_level="normal",
            industry=None,
        )
        assert score < 60

    @pytest_asyncio.fixture
    async def qualifier_with_lead(self, db_session: AsyncSession, sample_lead: Lead):
        """Create qualifier with a sample lead."""
        return LeadQualifierService(db_session), sample_lead

    @pytest.mark.asyncio
    async def test_qualify_lead(self, db_session: AsyncSession, sample_lead: Lead):
        """Test lead qualification."""
        qualifier = LeadQualifierService(db_session)

        qualified_lead = await qualifier.qualify_lead(sample_lead.id)

        assert qualified_lead.qualification_score is not None
        assert qualified_lead.budget_score is not None
        assert qualified_lead.urgency_score is not None
        assert qualified_lead.fit_score is not None
        assert qualified_lead.status in [LeadStatus.NEW, LeadStatus.QUALIFIED]

    @pytest.mark.asyncio
    async def test_qualify_lead_disqualification(self, db_session: AsyncSession, sample_source):
        """Test lead disqualification."""
        # Create a lead that should be disqualified
        lead = Lead(
            name="Spam Lead",
            original_request="Нужен сайт для казино бесплатно",
            source_id=sample_source.id,
            status=LeadStatus.NEW,
        )
        db_session.add(lead)
        await db_session.commit()
        await db_session.refresh(lead)

        qualifier = LeadQualifierService(db_session)
        qualified_lead = await qualifier.qualify_lead(lead.id)

        assert qualified_lead.status == LeadStatus.DISQUALIFIED
        assert qualified_lead.qualification_score == 0

    @pytest.mark.asyncio
    async def test_get_hot_leads(self, db_session: AsyncSession, qualified_lead: Lead):
        """Test getting hot leads."""
        qualifier = LeadQualifierService(db_session)

        hot_leads = await qualifier.get_hot_leads(limit=10)

        assert len(hot_leads) > 0
        assert all(lead.qualification_score >= 60 for lead in hot_leads)

"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base
from app.models import Lead, Source, Proposal, WebsiteAnalysis, LeadStatus, SourceType


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def sample_source(db_session: AsyncSession) -> Source:
    """Create a sample source for testing."""
    source = Source(
        name="Test Source",
        source_type=SourceType.TELEGRAM_CHANNEL,
        url="https://t.me/test",
        is_active=True,
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest_asyncio.fixture
async def sample_lead(db_session: AsyncSession, sample_source: Source) -> Lead:
    """Create a sample lead for testing."""
    lead = Lead(
        name="Test Lead",
        company_name="Test Company",
        email="test@example.com",
        telegram="@testuser",
        website="https://example.com",
        original_request="Нужен сайт для интернет-магазина",
        needs_description="Создать интернет-магазин одежды",
        budget_mentioned="100 тыс руб",
        urgency="high",
        source_id=sample_source.id,
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)
    return lead


@pytest_asyncio.fixture
async def qualified_lead(db_session: AsyncSession, sample_source: Source) -> Lead:
    """Create a qualified lead for testing."""
    lead = Lead(
        name="Hot Lead",
        company_name="Hot Company",
        email="hot@example.com",
        telegram="@hotuser",
        website="https://hot-company.com",
        original_request="Срочно нужен редизайн сайта, бюджет 200 тыс",
        needs_description="Редизайн корпоративного сайта",
        budget_mentioned="200 тыс руб",
        urgency="urgent",
        source_id=sample_source.id,
        status=LeadStatus.QUALIFIED,
        qualification_score=85.0,
        budget_score=80.0,
        urgency_score=95.0,
        fit_score=80.0,
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)
    return lead

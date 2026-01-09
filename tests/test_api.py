"""Tests for API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database import get_db
from app.models import Lead, Source, LeadStatus, SourceType


class TestLeadsAPI:
    """Tests for leads API endpoints."""

    @pytest_asyncio.fixture
    async def client(self, db_session: AsyncSession):
        """Create test client with database override."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_leads_empty(self, client: AsyncClient):
        """Test listing leads when empty."""
        response = await client.get("/api/leads")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_lead(self, client: AsyncClient):
        """Test creating a lead."""
        lead_data = {
            "name": "Test Lead",
            "email": "test@example.com",
            "original_request": "Need a website",
        }

        response = await client.post("/api/leads", json=lead_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Lead"
        assert data["email"] == "test@example.com"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_get_lead(self, client: AsyncClient, sample_lead: Lead):
        """Test getting a single lead."""
        response = await client.get(f"/api/leads/{sample_lead.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_lead.name
        assert data["email"] == sample_lead.email

    @pytest.mark.asyncio
    async def test_get_lead_not_found(self, client: AsyncClient):
        """Test getting non-existent lead."""
        response = await client.get("/api/leads/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_lead(self, client: AsyncClient, sample_lead: Lead):
        """Test updating a lead."""
        update_data = {"status": "contacted"}

        response = await client.patch(
            f"/api/leads/{sample_lead.id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "contacted"

    @pytest.mark.asyncio
    async def test_delete_lead(self, client: AsyncClient, sample_lead: Lead):
        """Test deleting a lead."""
        response = await client.delete(f"/api/leads/{sample_lead.id}")
        assert response.status_code == 204

        # Verify deletion
        response = await client.get(f"/api/leads/{sample_lead.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_leads_stats(self, client: AsyncClient, sample_lead: Lead):
        """Test getting leads statistics."""
        response = await client.get("/api/leads/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_status" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_qualify_lead(self, client: AsyncClient, sample_lead: Lead):
        """Test qualifying a lead."""
        response = await client.post(f"/api/leads/{sample_lead.id}/qualify")
        assert response.status_code == 200
        data = response.json()
        assert data["qualification_score"] is not None

    @pytest.mark.asyncio
    async def test_filter_leads_by_status(self, client: AsyncClient, sample_lead: Lead):
        """Test filtering leads by status."""
        response = await client.get("/api/leads?status=new")
        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "new" for item in data["items"])


class TestSourcesAPI:
    """Tests for sources API endpoints."""

    @pytest_asyncio.fixture
    async def client(self, db_session: AsyncSession):
        """Create test client with database override."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_sources(self, client: AsyncClient, sample_source: Source):
        """Test listing sources."""
        response = await client.get("/api/sources?active_only=false")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_create_source(self, client: AsyncClient):
        """Test creating a source."""
        source_data = {
            "name": "New Source",
            "source_type": "telegram_channel",
            "url": "https://t.me/newchannel",
        }

        response = await client.post("/api/sources", json=source_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Source"

    @pytest.mark.asyncio
    async def test_toggle_source(self, client: AsyncClient, sample_source: Source):
        """Test toggling source active status."""
        initial_status = sample_source.is_active

        response = await client.post(f"/api/sources/{sample_source.id}/toggle")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] != initial_status


class TestProposalsAPI:
    """Tests for proposals API endpoints."""

    @pytest_asyncio.fixture
    async def client(self, db_session: AsyncSession):
        """Create test client with database override."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_proposal(self, client: AsyncClient, sample_lead: Lead):
        """Test generating a proposal."""
        request_data = {
            "lead_id": sample_lead.id,
            "channel": "email",
            "tone": "professional",
        }

        response = await client.post("/api/proposals/generate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["lead_id"] == sample_lead.id
        assert data["content"] is not None
        assert len(data["content"]) > 0

    @pytest.mark.asyncio
    async def test_list_channels(self, client: AsyncClient):
        """Test listing proposal channels."""
        response = await client.get("/api/proposals/channels/list")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(ch["value"] == "email" for ch in data)


class TestSearchAPI:
    """Tests for search API endpoints."""

    @pytest_asyncio.fixture
    async def client(self, db_session: AsyncSession):
        """Create test client with database override."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_source_types(self, client: AsyncClient):
        """Test listing source types."""
        response = await client.get("/api/search/source-types")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_get_default_keywords(self, client: AsyncClient):
        """Test getting default keywords."""
        response = await client.get("/api/search/keywords/default")
        assert response.status_code == 200
        data = response.json()
        assert "keywords" in data
        assert len(data["keywords"]) > 0


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest_asyncio.fixture
    async def client(self, db_session: AsyncSession):
        """Create test client."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

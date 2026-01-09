"""Lead finder service - orchestrates lead discovery from multiple sources."""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead, Source, LeadStatus, SourceType
from app.parsers import (
    BaseParser,
    ParsedLead,
    TelegramParser,
    AvitoParser,
    FreelanceParser,
    ForumParser,
)
from app.config import settings


class LeadFinderService:
    """Service for finding and storing leads from multiple sources."""

    # Map source types to parser classes
    PARSER_REGISTRY = {
        SourceType.TELEGRAM_CHANNEL: TelegramParser,
        SourceType.CLASSIFIED_ADS: AvitoParser,
        SourceType.FREELANCE_PLATFORM: FreelanceParser,
        SourceType.FORUM: ForumParser,
    }

    def __init__(self, db: AsyncSession):
        """Initialize the lead finder service."""
        self.db = db

    async def get_or_create_source(
        self,
        name: str,
        source_type: SourceType,
        url: Optional[str] = None,
        **kwargs
    ) -> Source:
        """Get existing source or create a new one."""
        result = await self.db.execute(
            select(Source).where(
                Source.name == name,
                Source.source_type == source_type
            )
        )
        source = result.scalar_one_or_none()

        if not source:
            source = Source(
                name=name,
                source_type=source_type,
                url=url,
                **kwargs
            )
            self.db.add(source)
            await self.db.flush()

        return source

    async def check_duplicate(self, parsed_lead: ParsedLead) -> bool:
        """Check if a similar lead already exists."""
        # Check by source URL (most reliable)
        if parsed_lead.source_url:
            result = await self.db.execute(
                select(Lead).where(Lead.source_url == parsed_lead.source_url)
            )
            if result.scalar_one_or_none():
                return True

        # Check by email if available
        if parsed_lead.email:
            result = await self.db.execute(
                select(Lead).where(Lead.email == parsed_lead.email)
            )
            if result.scalar_one_or_none():
                return True

        # Check by telegram if available
        if parsed_lead.telegram:
            result = await self.db.execute(
                select(Lead).where(Lead.telegram == parsed_lead.telegram)
            )
            if result.scalar_one_or_none():
                return True

        return False

    async def create_lead_from_parsed(
        self,
        parsed_lead: ParsedLead,
        source: Source
    ) -> Lead:
        """Create a Lead model from parsed data."""
        lead = Lead(
            name=parsed_lead.name,
            company_name=parsed_lead.company_name,
            email=parsed_lead.email,
            phone=parsed_lead.phone,
            telegram=parsed_lead.telegram,
            website=parsed_lead.website,
            social_links=parsed_lead.social_links,
            business_description=parsed_lead.business_description,
            industry=parsed_lead.industry,
            original_request=parsed_lead.original_request,
            needs_description=parsed_lead.needs_description,
            budget_mentioned=parsed_lead.budget_mentioned,
            urgency=parsed_lead.urgency,
            source_id=source.id,
            source_url=parsed_lead.source_url,
            found_at=parsed_lead.found_at,
            status=LeadStatus.NEW,
        )

        self.db.add(lead)
        return lead

    async def search_source(
        self,
        parser: BaseParser,
        source: Source,
        max_results: int = 50
    ) -> list[Lead]:
        """Search a single source and store found leads."""
        leads_found = []
        new_leads = 0

        async for parsed_lead in parser.search(max_results):
            # Skip duplicates
            if await self.check_duplicate(parsed_lead):
                continue

            # Create and store lead
            lead = await self.create_lead_from_parsed(parsed_lead, source)
            leads_found.append(lead)
            new_leads += 1

            # Update source statistics
            source.total_leads_found += 1

        source.last_search_at = datetime.utcnow()

        return leads_found

    async def search_all_sources(
        self,
        max_results_per_source: int = 50,
        source_types: Optional[list[SourceType]] = None
    ) -> dict:
        """Search all configured sources for leads."""
        results = {
            "total_found": 0,
            "by_source": {},
            "errors": [],
        }

        # Get active sources
        query = select(Source).where(Source.is_active == True)
        if source_types:
            query = query.where(Source.source_type.in_(source_types))

        result = await self.db.execute(query)
        sources = result.scalars().all()

        # If no sources configured, use default parsers
        if not sources:
            sources = await self._create_default_sources()

        # Search each source
        for source in sources:
            try:
                parser_class = self.PARSER_REGISTRY.get(source.source_type)
                if not parser_class:
                    continue

                # Create parser with source configuration
                parser_config = source.parser_config or {}
                keywords = source.search_keywords

                parser = parser_class(keywords=keywords, **parser_config)

                # Perform search
                leads = await self.search_source(
                    parser,
                    source,
                    max_results_per_source
                )

                results["by_source"][source.name] = len(leads)
                results["total_found"] += len(leads)

            except Exception as e:
                error_msg = f"Error searching {source.name}: {str(e)}"
                results["errors"].append(error_msg)
                print(error_msg)

        await self.db.commit()
        return results

    async def _create_default_sources(self) -> list[Source]:
        """Create default sources if none exist."""
        default_sources = [
            {
                "name": "Telegram Channels",
                "source_type": SourceType.TELEGRAM_CHANNEL,
                "description": "Freelance and web development Telegram channels",
            },
            {
                "name": "Freelance Platforms",
                "source_type": SourceType.FREELANCE_PLATFORM,
                "description": "FL.ru, Kwork, Habr Freelance",
            },
            {
                "name": "Avito Services",
                "source_type": SourceType.CLASSIFIED_ADS,
                "url": "https://avito.ru",
                "description": "Avito classifieds - services section",
            },
            {
                "name": "Forums",
                "source_type": SourceType.FORUM,
                "description": "Web development forums",
            },
        ]

        sources = []
        for source_data in default_sources:
            source = await self.get_or_create_source(**source_data)
            sources.append(source)

        await self.db.flush()
        return sources

    async def search_custom(
        self,
        parser_type: SourceType,
        config: dict,
        source_name: str,
        max_results: int = 50
    ) -> list[Lead]:
        """Run a custom search with specific configuration."""
        parser_class = self.PARSER_REGISTRY.get(parser_type)
        if not parser_class:
            raise ValueError(f"Unknown parser type: {parser_type}")

        # Get or create source
        source = await self.get_or_create_source(
            name=source_name,
            source_type=parser_type,
            parser_config=config,
        )

        # Create parser and search
        parser = parser_class(**config)
        leads = await self.search_source(parser, source, max_results)

        await self.db.commit()
        return leads

    async def get_search_stats(self) -> dict:
        """Get statistics about searches and sources."""
        result = await self.db.execute(select(Source))
        sources = result.scalars().all()

        stats = {
            "total_sources": len(sources),
            "active_sources": sum(1 for s in sources if s.is_active),
            "total_leads_found": sum(s.total_leads_found for s in sources),
            "sources": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.source_type.value,
                    "leads_found": s.total_leads_found,
                    "last_search": s.last_search_at.isoformat() if s.last_search_at else None,
                }
                for s in sources
            ]
        }

        return stats

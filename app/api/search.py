"""API endpoints for lead search operations."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SourceType
from app.services import LeadFinderService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/run")
async def run_search(
    max_results_per_source: int = Query(50, ge=1, le=200),
    source_types: Optional[list[SourceType]] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Run a search across all configured sources."""
    finder = LeadFinderService(db)
    results = await finder.search_all_sources(
        max_results_per_source=max_results_per_source,
        source_types=source_types,
    )
    return results


@router.post("/run-background")
async def run_search_background(
    background_tasks: BackgroundTasks,
    max_results_per_source: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Start a search in the background."""
    # Note: For production, you'd want to use Celery or similar
    # This is a simplified background task

    async def search_task():
        finder = LeadFinderService(db)
        await finder.search_all_sources(max_results_per_source=max_results_per_source)

    background_tasks.add_task(search_task)

    return {"message": "Search started in background", "status": "running"}


@router.get("/stats")
async def get_search_stats(db: AsyncSession = Depends(get_db)):
    """Get search statistics."""
    finder = LeadFinderService(db)
    stats = await finder.get_search_stats()
    return stats


@router.post("/custom")
async def run_custom_search(
    source_name: str,
    parser_type: SourceType,
    max_results: int = Query(50, ge=1, le=200),
    keywords: Optional[list[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Run a custom search with specific configuration."""
    finder = LeadFinderService(db)

    config = {}
    if keywords:
        config["keywords"] = keywords

    try:
        leads = await finder.search_custom(
            parser_type=parser_type,
            config=config,
            source_name=source_name,
            max_results=max_results,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "source_name": source_name,
        "parser_type": parser_type.value,
        "leads_found": len(leads),
        "leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "source_url": lead.source_url,
            }
            for lead in leads
        ],
    }


@router.get("/source-types")
async def list_source_types():
    """List available source types for searching."""
    return [
        {
            "value": st.value,
            "name": st.name,
            "description": {
                SourceType.TELEGRAM_CHANNEL: "Telegram каналы и чаты",
                SourceType.TELEGRAM_CHAT: "Telegram чаты",
                SourceType.FORUM: "Форумы и сообщества",
                SourceType.FREELANCE_PLATFORM: "Фриланс-биржи (FL.ru, Kwork и др.)",
                SourceType.SOCIAL_MEDIA: "Социальные сети",
                SourceType.JOB_BOARD: "Доски объявлений о работе",
                SourceType.CLASSIFIED_ADS: "Доски объявлений (Avito и др.)",
                SourceType.DIRECTORY: "Бизнес-каталоги",
                SourceType.MANUAL: "Ручной ввод",
                SourceType.OTHER: "Другие источники",
            }.get(st, st.name),
        }
        for st in SourceType
    ]


@router.get("/keywords/default")
async def get_default_keywords():
    """Get default search keywords."""
    from app.parsers.base import BaseParser

    return {
        "keywords": BaseParser.DEFAULT_KEYWORDS,
        "description": "Ключевые слова для поиска клиентов, которым нужен сайт",
    }

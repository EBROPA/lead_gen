"""API endpoints for source management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Source, SourceType
from app.schemas import SourceCreate, SourceUpdate, SourceResponse

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
async def list_sources(
    source_type: Optional[SourceType] = None,
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """List all sources."""
    query = select(Source)

    if active_only:
        query = query.where(Source.is_active == True)
    if source_type:
        query = query.where(Source.source_type == source_type)

    query = query.order_by(Source.total_leads_found.desc())

    result = await db.execute(query)
    sources = result.scalars().all()

    return [SourceResponse.model_validate(source) for source in sources]


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single source by ID."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    return SourceResponse.model_validate(source)


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(
    source_data: SourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new source."""
    source = Source(**source_data.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return SourceResponse.model_validate(source)


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    source_data: SourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = source_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)

    return SourceResponse.model_validate(source)


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/toggle", response_model=SourceResponse)
async def toggle_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Toggle source active status."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.is_active = not source.is_active
    await db.commit()
    await db.refresh(source)

    return SourceResponse.model_validate(source)


@router.get("/types/list")
async def list_source_types():
    """List available source types."""
    return [
        {"value": st.value, "name": st.name}
        for st in SourceType
    ]

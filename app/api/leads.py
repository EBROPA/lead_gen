"""API endpoints for lead management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Lead, LeadStatus, WebsiteAnalysis
from app.schemas import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    LeadSearchFilters,
)
from app.services import LeadQualifierService, WebsiteAnalyzerService

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[LeadStatus] = None,
    min_score: Optional[float] = Query(None, ge=0, le=100),
    source_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List leads with pagination and filtering."""
    query = select(Lead).options(selectinload(Lead.website_analysis))

    # Apply filters
    if status:
        query = query.where(Lead.status == status)
    if min_score is not None:
        query = query.where(Lead.qualification_score >= min_score)
    if source_id:
        query = query.where(Lead.source_id == source_id)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            Lead.name.ilike(search_filter) |
            Lead.company_name.ilike(search_filter) |
            Lead.original_request.ilike(search_filter)
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.order_by(Lead.qualification_score.desc().nulls_last(), Lead.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    leads = result.scalars().all()

    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total or 0,
        page=page,
        per_page=per_page,
        pages=(total or 0 + per_page - 1) // per_page,
    )


@router.get("/hot", response_model=list[LeadResponse])
async def get_hot_leads(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get top qualified (hot) leads."""
    qualifier = LeadQualifierService(db)
    leads = await qualifier.get_hot_leads(limit)
    return [LeadResponse.model_validate(lead) for lead in leads]


@router.get("/stats")
async def get_leads_stats(db: AsyncSession = Depends(get_db)):
    """Get lead statistics."""
    # Total leads
    total = await db.scalar(select(func.count(Lead.id)))

    # By status
    status_counts = {}
    for status in LeadStatus:
        count = await db.scalar(
            select(func.count(Lead.id)).where(Lead.status == status)
        )
        status_counts[status.value] = count or 0

    # Average scores
    avg_score = await db.scalar(
        select(func.avg(Lead.qualification_score)).where(
            Lead.qualification_score.isnot(None)
        )
    )

    # Leads with contact
    with_contact = await db.scalar(
        select(func.count(Lead.id)).where(
            (Lead.email.isnot(None)) |
            (Lead.phone.isnot(None)) |
            (Lead.telegram.isnot(None))
        )
    )

    return {
        "total": total or 0,
        "by_status": status_counts,
        "average_score": round(avg_score, 2) if avg_score else None,
        "with_contact": with_contact or 0,
        "hot_leads": status_counts.get("qualified", 0),
    }


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single lead by ID."""
    result = await db.execute(
        select(Lead)
        .options(selectinload(Lead.website_analysis))
        .where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return LeadResponse.model_validate(lead)


@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new lead manually."""
    lead = Lead(**lead_data.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    await db.commit()
    await db.refresh(lead)

    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.delete(lead)
    await db.commit()


@router.post("/{lead_id}/qualify", response_model=LeadResponse)
async def qualify_lead(
    lead_id: int,
    use_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Qualify a lead and calculate scores."""
    qualifier = LeadQualifierService(db)

    try:
        if use_ai:
            lead = await qualifier.qualify_lead_with_ai(lead_id)
        else:
            lead = await qualifier.qualify_lead(lead_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return LeadResponse.model_validate(lead)


@router.post("/{lead_id}/analyze-website")
async def analyze_lead_website(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Analyze the website associated with a lead."""
    analyzer = WebsiteAnalyzerService(db)

    try:
        analysis = await analyzer.analyze_lead_website(lead_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not analysis:
        raise HTTPException(status_code=400, detail="Lead has no website to analyze")

    return {
        "lead_id": lead_id,
        "url": analysis.url,
        "is_accessible": analysis.is_accessible,
        "overall_score": analysis.overall_score,
        "issues": analysis.issues,
        "suggestions": analysis.improvement_suggestions,
    }


@router.post("/qualify-all")
async def qualify_all_leads(
    use_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Qualify all new leads."""
    qualifier = LeadQualifierService(db)
    results = await qualifier.qualify_all_new_leads(use_ai=use_ai)
    return results


@router.post("/analyze-all-websites")
async def analyze_all_websites(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Analyze websites for all leads that haven't been analyzed."""
    analyzer = WebsiteAnalyzerService(db)
    results = await analyzer.analyze_all_leads_websites(limit=limit)
    return results

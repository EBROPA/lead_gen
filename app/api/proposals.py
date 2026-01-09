"""API endpoints for proposal management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Proposal, ProposalStatus, ProposalChannel
from app.schemas import (
    ProposalCreate,
    ProposalUpdate,
    ProposalResponse,
    ProposalGenerateRequest,
    ProposalGenerateResponse,
)
from app.services import ProposalGeneratorService

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("", response_model=list[ProposalResponse])
async def list_proposals(
    lead_id: Optional[int] = None,
    status: Optional[ProposalStatus] = None,
    channel: Optional[ProposalChannel] = None,
    db: AsyncSession = Depends(get_db),
):
    """List proposals with optional filtering."""
    query = select(Proposal)

    if lead_id:
        query = query.where(Proposal.lead_id == lead_id)
    if status:
        query = query.where(Proposal.status == status)
    if channel:
        query = query.where(Proposal.channel == channel)

    query = query.order_by(Proposal.created_at.desc())

    result = await db.execute(query)
    proposals = result.scalars().all()

    return [ProposalResponse.model_validate(p) for p in proposals]


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single proposal by ID."""
    result = await db.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return ProposalResponse.model_validate(proposal)


@router.post("/generate", response_model=ProposalResponse)
async def generate_proposal(
    request: ProposalGenerateRequest,
    use_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new proposal for a lead."""
    generator = ProposalGeneratorService(db)

    try:
        if use_ai:
            proposal = await generator.generate_proposal_with_ai(
                lead_id=request.lead_id,
                channel=request.channel,
                tone=request.tone,
                custom_instructions=request.custom_notes,
            )
        else:
            proposal = await generator.generate_proposal(
                lead_id=request.lead_id,
                channel=request.channel,
                tone=request.tone,
                include_portfolio=request.include_portfolio,
                include_website_analysis=request.include_website_analysis,
                custom_notes=request.custom_notes,
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ProposalResponse.model_validate(proposal)


@router.post("", response_model=ProposalResponse, status_code=201)
async def create_proposal(
    proposal_data: ProposalCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a proposal manually."""
    proposal = Proposal(**proposal_data.model_dump())
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return ProposalResponse.model_validate(proposal)


@router.patch("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: int,
    proposal_data: ProposalUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a proposal."""
    result = await db.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    update_data = proposal_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(proposal, field, value)

    await db.commit()
    await db.refresh(proposal)

    return ProposalResponse.model_validate(proposal)


@router.delete("/{proposal_id}", status_code=204)
async def delete_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a proposal."""
    result = await db.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    await db.delete(proposal)
    await db.commit()


@router.post("/{proposal_id}/mark-sent", response_model=ProposalResponse)
async def mark_proposal_sent(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark a proposal as sent."""
    generator = ProposalGeneratorService(db)

    try:
        proposal = await generator.mark_proposal_sent(proposal_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ProposalResponse.model_validate(proposal)


@router.get("/channels/list")
async def list_proposal_channels():
    """List available proposal channels."""
    return [
        {"value": ch.value, "name": ch.name}
        for ch in ProposalChannel
    ]


@router.get("/statuses/list")
async def list_proposal_statuses():
    """List available proposal statuses."""
    return [
        {"value": st.value, "name": st.name}
        for st in ProposalStatus
    ]

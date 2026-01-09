"""API routers."""

from app.api.leads import router as leads_router
from app.api.sources import router as sources_router
from app.api.proposals import router as proposals_router
from app.api.search import router as search_router

__all__ = [
    "leads_router",
    "sources_router",
    "proposals_router",
    "search_router",
]

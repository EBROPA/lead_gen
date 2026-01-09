"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import init_db, close_db
from app.api import leads_router, sources_router, proposals_router, search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Automated lead generation system for web development services",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include API routers
app.include_router(leads_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(proposals_router, prefix="/api")
app.include_router(search_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


@app.get("/api")
async def api_info():
    """API information."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "endpoints": {
            "leads": "/api/leads",
            "sources": "/api/sources",
            "proposals": "/api/proposals",
            "search": "/api/search",
        },
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )

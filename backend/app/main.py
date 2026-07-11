"""
PAC Backend — FastAPI Application Entry Point

Wires together:
  - Middleware (CORS)
  - Exception handlers
  - API routers (auth, crimes, criminals)
  - Health check endpoints
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import setup_exception_handlers
from app.api.v1.routers import auth, crimes, criminals

# Setup logging before all other imports that might log
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown hooks."""
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} "
        f"[{settings.ENVIRONMENT.upper()}]"
    )
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


# ── FastAPI Application ────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**PAC — PoliceIT Analytics Core**\n\n"
        "AI-powered investigation intelligence platform for Karnataka State Police.\n"
        "Transforms static crime records into actionable behavioural intelligence.\n\n"
        "### Intelligence Architecture\n"
        "- **Crime DNA**: 384-dim vector embeddings via Sentence Transformers\n"
        "- **MO Intelligence**: Rule-based feature extraction from narratives\n"
        "- **Similarity Engine**: pgvector cosine search\n"
        "- **Criminal Networks**: Neo4j graph database\n"
        "- **Geo Intelligence**: PostGIS hotspot detection\n"
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    contact={
        "name": "PAC Development Team",
        "email": "pac@ksp.gov.in",
    },
)

# ── CORS ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ─────────────────────────────────────
setup_exception_handlers(app)

# ── API Routers ────────────────────────────────────────────
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)
app.include_router(
    crimes.router,
    prefix="/api/v1/crimes",
    tags=["Crime Registration"],
)
app.include_router(
    criminals.router,
    prefix="/api/v1/criminals",
    tags=["Criminal Profiles"],
)


# ── Health Endpoints ───────────────────────────────────────
@app.get("/health", tags=["Health"], include_in_schema=False)
async def health_check():
    """Docker health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/v1/health", tags=["Health"])
async def api_health():
    """API-level health check with version info."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

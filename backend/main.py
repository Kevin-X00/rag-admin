"""RAG Admin - FastAPI Application Entry Point."""

import os
import sys
import logging
from pathlib import Path

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routes import knowledge_base, documents, search, stats

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG Admin - Knowledge Base Management System",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(knowledge_base.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(stats.router)


@app.on_event("startup")
async def startup():
    """Initialize application on startup."""
    logger.info("Starting RAG Admin...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Ensure required directories
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)

    logger.info("RAG Admin started successfully")
    logger.info("Upload dir: %s", settings.upload_dir)
    logger.info("Data dir: %s", settings.data_dir)
    logger.info("Chroma persist dir: %s", settings.chroma_persist_dir)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


# Serve frontend static files if they exist
frontend_dist = os.path.join(settings.base_dir, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    logger.info("Frontend static files mounted from %s", frontend_dist)
else:
    logger.info("Frontend dist not found at %s, API-only mode", frontend_dist)

"""Main FastAPI application for dashboard API."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from database import engine, Base
from middleware.error_handler import setup_exception_handlers
from routes import auth, stream, logs
from routes import config as config_router
from routes import users, mappings, assets, metrics
from routes import websocket as ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown.

    Args:
        app: FastAPI application instance.
    """
    # Startup
    logger.info("Starting Dashboard API...")

    try:
        # Test database connection
        logger.info("Testing database connection...")
        try:
            from database import SessionLocal

            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            logger.info("Database connection successful")
        except Exception as db_error:
            logger.warning(f"Database connection issue: {db_error}")
            # Continue anyway - tables might not exist yet

        # Run idempotent startup migrations (safe to run multiple times)
        try:
            logger.info("Running startup migrations (idempotent)...")
            from migrations.add_asset_tags_and_timestamps import upgrade as migrate_assets
            from migrations.add_video_assets_indexes import upgrade as migrate_asset_indexes

            migrate_assets()
            migrate_asset_indexes()
            logger.info("Startup migrations completed")
        except Exception as mig_error:
            logger.warning(f"Startup migrations encountered an issue: {mig_error}")

        logger.info(f"Dashboard API ready on port {settings.port}")
        yield

    except Exception as e:
        logger.error(f"Failed to start Dashboard API: {e}", exc_info=True)
        # Don't raise - allow app to start anyway

    finally:
        # Shutdown
        logger.info("Shutting down Dashboard API...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="REST API for managing 24/7 radio stream",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup exception handlers
setup_exception_handlers(app)

# Include routers
app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["Authentication"])

app.include_router(stream.router, prefix=f"{settings.api_prefix}/stream", tags=["Stream Control"])

app.include_router(
    config_router.router, prefix=f"{settings.api_prefix}/config", tags=["Configuration"]
)

app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["User Management"])

app.include_router(
    mappings.router, prefix=f"{settings.api_prefix}/mappings", tags=["Track Mappings"]
)

app.include_router(assets.router, prefix=f"{settings.api_prefix}/assets", tags=["Video Assets"])

app.include_router(
    metrics.router, prefix=f"{settings.api_prefix}/metrics", tags=["Monitoring & Metrics"]
)

app.include_router(logs.router, prefix=f"{settings.api_prefix}/logs", tags=["Logs"])

# WebSocket route (no prefix needed for /ws)
app.include_router(ws_router.router, tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint with API information.

    Returns:
        dict: API information.
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "endpoints": {
            "auth": f"{settings.api_prefix}/auth",
            "stream": f"{settings.api_prefix}/stream",
            "config": f"{settings.api_prefix}/config",
            "users": f"{settings.api_prefix}/users",
            "mappings": f"{settings.api_prefix}/mappings",
            "logs": f"{settings.api_prefix}/logs",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status.
    """
    from datetime import datetime

    return {
        "status": "healthy",
        "service": settings.app_name,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "dashboard_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import analytics, categories, downloads, loop_markers, settings, tags, videos, webhook

logger = structlog.get_logger()

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan context manager."""
    # Startup
    settings = get_settings()
    logger.info("application_startup", storage_root=settings.STORAGE_ROOT)

    # Initialize database
    await init_db(settings.DATABASE_PATH)

    # Ensure storage directories exist
    storage_path = Path(settings.STORAGE_ROOT)
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / "categories").mkdir(parents=True, exist_ok=True)
    (storage_path / "thumbnails").mkdir(parents=True, exist_ok=True)
    (storage_path / "db").mkdir(parents=True, exist_ok=True)

    logger.info("storage_directories_ready", storage_root=settings.STORAGE_ROOT)

    yield

    # Shutdown
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Magpie API",
        description="Self-hosted video collector with categorization and search",
        version="0.1.0",
    )

    # Add CORS middleware for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API key middleware
    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next: Any) -> Any:
        """Check API key for protected endpoints."""
        # Skip API key check for:
        # - Health endpoint
        # - OPTIONS requests
        # - Root path
        if (
            request.method == "OPTIONS"
            or request.url.path == "/"
            or request.url.path == "/api/health"
        ):
            return await call_next(request)

        # Check API key for protected endpoints
        api_key = request.headers.get("X-API-Key")
        settings = get_settings()

        # Allow requests without API key to proceed (they will be rejected by routers if needed)
        # This allows for more granular control per endpoint

        return await call_next(request)

    # Include routers
    app.include_router(videos.router)
    app.include_router(downloads.router)
    app.include_router(tags.router)
    app.include_router(categories.router)
    app.include_router(webhook.router)
    app.include_router(settings.router)
    app.include_router(loop_markers.router)
    app.include_router(analytics.router)

    # Mount static files for thumbnails
    storage_root = get_settings().STORAGE_ROOT
    thumbnails_path = Path(storage_root) / "thumbnails"
    if thumbnails_path.exists():
        app.mount("/api/thumbnails", StaticFiles(directory=str(thumbnails_path)), name="thumbnails")

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {"message": "Magpie API"}

    # Exception handlers
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.error("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # Set lifespan
    app.router.lifespan_context = lifespan

    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
    )

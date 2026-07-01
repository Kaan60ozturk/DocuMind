"""FastAPI application factory: CORS, routers, static frontend mount."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, load_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Tests pass their own ``settings`` (and fakes)."""
    settings = settings or load_settings()
    settings.ensure_dirs()

    app = FastAPI(title="DocuMind", version="0.1.0")
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


# Run with: uvicorn app.main:create_app --factory
# (a plain module-level ``app`` would require GEMINI_API_KEY just to import
# this module, which would break offline tests)

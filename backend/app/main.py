"""FastAPI application factory: state wiring, CORS, routers, static frontend."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, documents
from app.config import Settings, load_settings
from app.db.documents import DocumentRegistry
from app.db.vectorstore import VectorStore
from app.providers.base import EmbeddingProvider, LLMProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(
    settings: Settings | None = None,
    *,
    embedder: EmbeddingProvider | None = None,
    llm: LLMProvider | None = None,
) -> FastAPI:
    """Build the application. Tests inject fake providers here."""
    settings = settings or load_settings()
    settings.ensure_dirs()

    if embedder is None or llm is None:
        # Imported lazily so offline tests never touch the Gemini SDK path.
        from app.providers.gemini import GeminiProvider

        provider = GeminiProvider(settings)
        embedder = embedder or provider
        llm = llm or provider

    app = FastAPI(title="DocuMind", version="0.1.0")
    app.state.settings = settings
    app.state.embedder = embedder
    app.state.llm = llm
    app.state.registry = DocumentRegistry(settings.sqlite_path)
    app.state.vectorstore = VectorStore(settings.chroma_dir)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(documents.router)
    app.include_router(chat.router)

    # In production the built frontend is served by this same process.
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


# Run with: uvicorn app.main:create_app --factory
# (a plain module-level ``app`` would require GEMINI_API_KEY just to import
# this module, which would break offline tests)

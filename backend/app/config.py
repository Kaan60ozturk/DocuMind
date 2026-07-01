"""Typed, environment-driven application settings."""

from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# The repository root (this file lives at backend/app/config.py). The .env
# file is documented to live here, so find it regardless of the CWD the
# server was started from (repo root, backend/, or the Docker workdir).
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All runtime configuration, mapped 1:1 to environment variables.

    ``GEMINI_API_KEY`` intentionally has no default so a missing key fails
    fast at startup instead of surfacing as a confusing 401 mid-request.
    """

    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", ".env"),  # later entries win on conflict
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    chunk_size: int = 1200
    chunk_overlap: int = 200
    top_k: int = 5
    min_similarity: float = 0.25
    max_file_mb: int = 20
    data_dir: Path = Path("./data")
    allowed_origins: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "docmind.sqlite3"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """Load settings from the environment, failing fast with a clear message."""
    try:
        return Settings()
    except ValidationError as exc:
        missing = [str(err["loc"][0]).upper() for err in exc.errors() if err["type"] == "missing"]
        if missing:
            raise RuntimeError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Copy .env.example to .env and fill in your GEMINI_API_KEY "
                "(get a free key at https://aistudio.google.com/apikey)."
            ) from exc
        raise
